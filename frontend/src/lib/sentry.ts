/**
 * Optional Sentry instrumentation for the React frontend.
 *
 * Sentry is initialised only when VITE_SENTRY_DSN is set. With no DSN this
 * module is a no-op so local dev and CI builds incur zero network overhead.
 */
import * as Sentry from '@sentry/react'

let initialized = false

export function initSentry(): boolean {
  if (initialized) return true

  const dsn = import.meta.env.VITE_SENTRY_DSN
  if (!dsn) {
    return false
  }

  const environment = import.meta.env.VITE_SENTRY_ENVIRONMENT || import.meta.env.MODE
  const release = import.meta.env.VITE_SENTRY_RELEASE
  const tracesSampleRate = Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? '0')
  const replaysSampleRate = Number(import.meta.env.VITE_SENTRY_REPLAYS_SAMPLE_RATE ?? '0')

  Sentry.init({
    dsn,
    environment,
    release,
    tracesSampleRate: Number.isFinite(tracesSampleRate) ? tracesSampleRate : 0,
    replaysSessionSampleRate: Number.isFinite(replaysSampleRate) ? replaysSampleRate : 0,
    replaysOnErrorSampleRate: 1.0,
    integrations: [
      // Browser tracing + replay are auto-included when their sample rates are > 0.
    ],
  })

  initialized = true
  return true
}

export function isSentryInitialized(): boolean {
  return initialized
}

/**
 * Capture an exception manually (e.g. from an error handler that already
 * displayed UI feedback to the user).
 */
export function captureException(error: unknown, context?: Record<string, unknown>): void {
  if (!initialized) return
  Sentry.captureException(error, context ? { extra: context } : undefined)
}
