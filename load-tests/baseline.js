/**
 * k6 baseline load test - sustained traffic on read-mostly endpoints.
 *
 * Models a "typical hour": login once per VU, then alternate between health
 * checks, listing endpoints, and a code-analysis call. Targets endpoints that
 * do not modify shared state so the run is repeatable.
 *
 * Usage:
 *   k6 run load-tests/baseline.js
 *   BASE_URL=http://localhost:8000 USERNAME=demo PASSWORD=demo123456 k6 run load-tests/baseline.js
 */
import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const USERNAME = __ENV.USERNAME || 'demo';
const PASSWORD = __ENV.PASSWORD || 'demo123456';

const loginLatency = new Trend('login_latency_ms');
const analyzeLatency = new Trend('analyze_latency_ms');
const authErrors = new Rate('auth_error_rate');

export const options = {
  stages: [
    { duration: '20s', target: 10 },   // ramp up
    { duration: '1m',  target: 10 },   // hold
    { duration: '20s', target: 25 },   // step up
    { duration: '1m',  target: 25 },   // hold
    { duration: '20s', target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_failed: ['rate<0.02'],         // <2% errors
    http_req_duration: ['p(95)<2000'],      // p95 under 2s
    'analyze_latency_ms': ['p(95)<3000'],   // analysis can be heavier
    'auth_error_rate': ['rate<0.01'],
  },
};

function login() {
  const start = Date.now();
  const res = http.post(`${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ username: USERNAME, password: PASSWORD }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  loginLatency.add(Date.now() - start);

  const ok = check(res, {
    'login 200': (r) => r.status === 200,
    'login returns access_token': (r) => Boolean(r.json('access_token')),
  });
  authErrors.add(!ok);

  return ok ? res.json('access_token') : null;
}

export function setup() {
  // Verify the server is reachable before the run begins.
  const res = http.get(`${BASE_URL}/health`);
  if (res.status !== 200) {
    throw new Error(`Server not healthy at ${BASE_URL}: ${res.status}`);
  }
  return {};
}

export default function () {
  const token = login();
  if (!token) {
    sleep(1);
    return;
  }
  const authHeaders = {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  };

  group('read traffic', () => {
    check(http.get(`${BASE_URL}/health`), { 'health 200': (r) => r.status === 200 });
    check(http.get(`${BASE_URL}/api/v1/projects`, authHeaders),
      { 'projects 200 or 401': (r) => r.status === 200 || r.status === 401 });
  });

  group('code analysis', () => {
    const payload = JSON.stringify({
      code: 'def add(a, b):\n    if a > 0:\n        return a + b\n    return b\n',
      language: 'python',
    });
    const start = Date.now();
    const res = http.post(`${BASE_URL}/api/v1/code-analysis/structure`, payload, authHeaders);
    analyzeLatency.add(Date.now() - start);
    check(res, {
      'analyze 200 or 401': (r) => r.status === 200 || r.status === 401,
    });
  });

  sleep(1);
}
