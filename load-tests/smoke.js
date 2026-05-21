/**
 * k6 smoke test - sanity check that the API is up and responsive.
 *
 * Usage: k6 run load-tests/smoke.js
 *        BASE_URL=http://localhost:8000 k6 run load-tests/smoke.js
 */
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
  vus: 1,
  duration: '30s',
  thresholds: {
    // Fail the run if any check fails or any request exceeds 1s.
    checks: ['rate>0.99'],
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1000'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/health`);
  check(res, {
    'health 200': (r) => r.status === 200,
    'health body ok': (r) => r.json('status') === 'healthy',
  });
  sleep(1);
}
