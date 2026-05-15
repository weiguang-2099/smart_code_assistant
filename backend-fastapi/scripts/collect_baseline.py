"""
Performance baseline collection script.

This script collects performance metrics and calculates baseline values
for all API endpoints. Run this script periodically to update baselines.

Usage:
    python scripts/collect_baseline.py [--hours 24] [--output baseline.json]
"""
import asyncio
import argparse
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from app.database import AsyncSessionLocal, engine
from app.models.performance import PerformanceMetric, PerformanceBaseline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def calculate_percentile(values: list, percentile: float) -> float:
    """Calculate percentile value from a sorted list."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile / 100)
    index = min(index, len(sorted_values) - 1)
    return sorted_values[index]


async def collect_baseline(
    hours: int = 24,
    min_samples: int = 10,
    output_file: Optional[str] = None
) -> dict:
    """
    Collect performance baseline from recent metrics.

    Args:
        hours: Number of hours to look back
        min_samples: Minimum samples required for baseline
        output_file: Optional file to save baseline JSON

    Returns:
        Dictionary with baseline data
    """
    async with AsyncSessionLocal() as session:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        result = await session.execute(
            select(PerformanceMetric)
            .where(PerformanceMetric.created_at >= cutoff_time)
            .order_by(PerformanceMetric.endpoint, PerformanceMetric.method)
        )
        metrics = result.scalars().all()

        endpoint_data = {}
        for metric in metrics:
            key = f"{metric.method} {metric.endpoint}"
            if key not in endpoint_data:
                endpoint_data[key] = {
                    "method": metric.method,
                    "endpoint": metric.endpoint,
                    "response_times": [],
                    "errors": 0,
                    "total_count": 0,
                }
            endpoint_data[key]["response_times"].append(metric.response_time_ms)
            endpoint_data[key]["total_count"] += 1
            if metric.status_code >= 400:
                endpoint_data[key]["errors"] += 1

        baselines = {}
        report = {
            "collection_time": datetime.utcnow().isoformat(),
            "period_hours": hours,
            "total_metrics": len(metrics),
            "endpoints": {},
        }

        for key, data in endpoint_data.items():
            if len(data["response_times"]) < min_samples:
                logger.warning(f"Skipping {key}: only {len(data['response_times'])} samples (min: {min_samples})")
                continue

            times = data["response_times"]
            baselines[key] = {
                "method": data["method"],
                "endpoint": data["endpoint"],
                "p50_ms": await calculate_percentile(times, 50),
                "p95_ms": await calculate_percentile(times, 95),
                "p99_ms": await calculate_percentile(times, 99),
                "avg_ms": sum(times) / len(times),
                "min_ms": min(times),
                "max_ms": max(times),
                "sample_count": len(times),
                "error_count": data["errors"],
                "error_rate": data["errors"] / data["total_count"] * 100,
            }

            report["endpoints"][key] = baselines[key]

            existing_result = await session.execute(
                select(PerformanceBaseline)
                .where(
                    PerformanceBaseline.endpoint == data["endpoint"],
                    PerformanceBaseline.method == data["method"]
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                existing.p50_ms = baselines[key]["p50_ms"]
                existing.p95_ms = baselines[key]["p95_ms"]
                existing.p99_ms = baselines[key]["p99_ms"]
                existing.avg_ms = baselines[key]["avg_ms"]
                existing.min_ms = baselines[key]["min_ms"]
                existing.max_ms = baselines[key]["max_ms"]
                existing.sample_count = baselines[key]["sample_count"]
                existing.period_start = cutoff_time
                existing.period_end = datetime.utcnow()
                existing.updated_at = datetime.utcnow()
                logger.info(f"Updated baseline for {key}")
            else:
                baseline = PerformanceBaseline(
                    endpoint=data["endpoint"],
                    method=data["method"],
                    p50_ms=baselines[key]["p50_ms"],
                    p95_ms=baselines[key]["p95_ms"],
                    p99_ms=baselines[key]["p99_ms"],
                    avg_ms=baselines[key]["avg_ms"],
                    min_ms=baselines[key]["min_ms"],
                    max_ms=baselines[key]["max_ms"],
                    sample_count=baselines[key]["sample_count"],
                    period_start=cutoff_time,
                    period_end=datetime.utcnow(),
                )
                session.add(baseline)
                logger.info(f"Created baseline for {key}")

        await session.commit()

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"Baseline report saved to {output_file}")

        return report


def print_report(report: dict) -> None:
    """Print a formatted baseline report."""
    print("\n" + "=" * 80)
    print("PERFORMANCE BASELINE REPORT")
    print("=" * 80)
    print(f"\nCollection Time: {report['collection_time']}")
    print(f"Period: {report['period_hours']} hours")
    print(f"Total Metrics: {report['total_metrics']}")
    print(f"Endpoints: {len(report['endpoints'])}")

    print("\n" + "-" * 80)
    print(f"{'Endpoint':<50} {'P50':>8} {'P95':>8} {'P99':>8} {'Count':>8}")
    print("-" * 80)

    for key, data in sorted(report['endpoints'].items()):
        endpoint_display = f"{data['method']} {data['endpoint']}"
        if len(endpoint_display) > 48:
            endpoint_display = endpoint_display[:45] + "..."
        print(f"{endpoint_display:<50} {data['p50_ms']:>7.1f} {data['p95_ms']:>7.1f} {data['p99_ms']:>7.1f} {data['sample_count']:>8}")

    print("-" * 80)

    slow_endpoints = [
        (k, v) for k, v in report['endpoints'].items()
        if v['p95_ms'] > 500
    ]
    if slow_endpoints:
        print("\n⚠️  SLOW ENDPOINTS (P95 > 500ms):")
        for key, data in slow_endpoints:
            print(f"  - {key}: P95 = {data['p95_ms']:.1f}ms")

    error_endpoints = [
        (k, v) for k, v in report['endpoints'].items()
        if v['error_rate'] > 1
    ]
    if error_endpoints:
        print("\n⚠️  HIGH ERROR RATE (>1%):")
        for key, data in error_endpoints:
            print(f"  - {key}: Error Rate = {data['error_rate']:.2f}%")

    print("\n" + "=" * 80)


async def main():
    parser = argparse.ArgumentParser(description="Collect performance baseline")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back (default: 24)")
    parser.add_argument("--min-samples", type=int, default=10, help="Minimum samples required (default: 10)")
    parser.add_argument("--output", type=str, help="Output file for baseline JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress report output")
    args = parser.parse_args()

    logger.info(f"Collecting baseline for last {args.hours} hours...")

    report = await collect_baseline(
        hours=args.hours,
        min_samples=args.min_samples,
        output_file=args.output
    )

    if not args.quiet:
        print_report(report)

    logger.info("Baseline collection complete")


if __name__ == "__main__":
    asyncio.run(main())
