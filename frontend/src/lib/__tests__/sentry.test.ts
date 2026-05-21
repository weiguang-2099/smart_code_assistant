import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Mock the SDK before importing the module under test.
vi.mock('@sentry/react', () => ({
  init: vi.fn(),
  captureException: vi.fn(),
}))

import * as Sentry from '@sentry/react'

import { captureException, initSentry, isSentryInitialized } from '../sentry'

const stubEnv = (env: Record<string, string | undefined>) => {
  for (const [k, v] of Object.entries(env)) {
    vi.stubEnv(k, v ?? '')
  }
}

beforeEach(() => {
  // Reset the module-private init flag between tests by reloading the module.
  vi.resetModules()
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.clearAllMocks()
})

describe('initSentry', () => {
  it('returns false when VITE_SENTRY_DSN is not set', async () => {
    stubEnv({ VITE_SENTRY_DSN: undefined })
    const { initSentry, isSentryInitialized } = await import('../sentry')

    expect(initSentry()).toBe(false)
    expect(isSentryInitialized()).toBe(false)
    expect(Sentry.init).not.toHaveBeenCalled()
  })

  it('initialises and returns true when DSN is set', async () => {
    stubEnv({ VITE_SENTRY_DSN: 'https://x@sentry.io/1' })
    const { initSentry, isSentryInitialized } = await import('../sentry')

    expect(initSentry()).toBe(true)
    expect(isSentryInitialized()).toBe(true)
    expect(Sentry.init).toHaveBeenCalledOnce()
  })

  it('does not re-initialise on subsequent calls', async () => {
    stubEnv({ VITE_SENTRY_DSN: 'https://x@sentry.io/1' })
    const { initSentry } = await import('../sentry')

    initSentry()
    initSentry()
    expect(Sentry.init).toHaveBeenCalledOnce()
  })

  it('passes traces/replay sample rates from env', async () => {
    stubEnv({
      VITE_SENTRY_DSN: 'https://x@sentry.io/1',
      VITE_SENTRY_TRACES_SAMPLE_RATE: '0.3',
      VITE_SENTRY_REPLAYS_SAMPLE_RATE: '0.2',
    })
    const { initSentry } = await import('../sentry')
    initSentry()

    const call = (Sentry.init as unknown as { mock: { calls: Array<[Record<string, unknown>]> } })
      .mock.calls[0][0]
    expect(call.tracesSampleRate).toBe(0.3)
    expect(call.replaysSessionSampleRate).toBe(0.2)
  })

  it('falls back to 0 when sample rate envs are missing or invalid', async () => {
    stubEnv({
      VITE_SENTRY_DSN: 'https://x@sentry.io/1',
      VITE_SENTRY_TRACES_SAMPLE_RATE: 'not-a-number',
    })
    const { initSentry } = await import('../sentry')
    initSentry()
    const call = (Sentry.init as unknown as { mock: { calls: Array<[Record<string, unknown>]> } })
      .mock.calls[0][0]
    expect(call.tracesSampleRate).toBe(0)
  })
})

describe('captureException', () => {
  it('is a no-op before init', () => {
    captureException(new Error('boom'))
    expect(Sentry.captureException).not.toHaveBeenCalled()
  })

  it('forwards to Sentry after init', async () => {
    stubEnv({ VITE_SENTRY_DSN: 'https://x@sentry.io/1' })
    const { initSentry, captureException } = await import('../sentry')
    initSentry()

    const err = new Error('boom')
    captureException(err, { route: '/x' })

    expect(Sentry.captureException).toHaveBeenCalledWith(err, { extra: { route: '/x' } })
  })
})
