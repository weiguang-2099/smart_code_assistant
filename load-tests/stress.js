/**
 * k6 stress test - push the API past its comfortable limit to find the knee.
 *
 * Run for ~5 minutes; observe where p95 latency or error rate starts to climb.
 *
 * Usage: k6 run load-tests/stress.js
 */
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
  stages: [
    { duration: '30s', target: 50 },
    { duration: '1m',  target: 100 },
    { duration: '1m',  target: 200 },
    { duration: '1m',  target: 400 },
    { duration: '1m',  target: 800 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    // Soft thresholds; failure here is informational rather than a hard stop.
    http_req_failed: ['rate<0.15'],
    http_req_duration: ['p(95)<5000'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/health`);
  check(res, { '2xx': (r) => r.status >= 200 && r.status < 300 });
  sleep(0.2);
}
