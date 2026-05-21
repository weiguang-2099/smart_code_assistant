# Load tests

HTTP-level load tests written for [k6](https://k6.io/). Three scenarios:

| Scenario | File | Purpose |
|---|---|---|
| `smoke` | `smoke.js` | 30s @ 1 VU. Sanity-check the API is up. Hard-fails on any 5xx. |
| `baseline` | `baseline.js` | Stepped 10 -> 25 VUs over ~3 min. Sustained read traffic on auth + analysis endpoints. Hard p95 budget. |
| `stress` | `stress.js` | 50 -> 800 VUs over ~5 min. Push past the knee to find the breaking point. |

## Prerequisites

```bash
# macOS
brew install k6

# Windows (Chocolatey)
choco install k6

# Or download from https://k6.io/docs/get-started/installation/
```

Start the backend stack first:

```bash
docker compose up -d
cd backend-fastapi
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Running

```bash
# from project root

# 30s smoke test
k6 run load-tests/smoke.js

# 3-min baseline (uses the seeded demo user by default)
k6 run load-tests/baseline.js

# point at a different deployment
BASE_URL=https://api.example.com k6 run load-tests/baseline.js

# pass non-default credentials
USERNAME=alice PASSWORD=secret k6 run load-tests/baseline.js

# 5-min stress
k6 run load-tests/stress.js
```

## Thresholds

Each scenario embeds pass/fail thresholds so the run exits non-zero if the
service regresses. Edit the `thresholds` block in each file to tune.

| Scenario | http_req_failed | http_req_duration p95 |
|---|---|---|
| smoke | < 1% | < 1000 ms |
| baseline | < 2% | < 2000 ms |
| stress | < 15% (informational) | < 5000 ms |

The baseline scenario additionally tracks custom metrics:
- `login_latency_ms` - JWT issue time
- `analyze_latency_ms` - p95 budget < 3000 ms
- `auth_error_rate` - < 1%
