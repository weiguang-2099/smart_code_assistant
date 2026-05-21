import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'

import ErrorBoundary, {
  NetworkErrorFallback,
  withErrorBoundary,
} from '../ErrorBoundary'

function Throws({ message = 'kaboom' }: { message?: string }): never {
  throw new Error(message)
}

function Ok() {
  return <div data-testid="ok">child rendered</div>
}

// React logs the caught error to console.error - mute it for clean output.
beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ErrorBoundary', () => {
  it('renders children when nothing throws', () => {
    render(
      <ErrorBoundary>
        <Ok />
      </ErrorBoundary>
    )
    expect(screen.getByTestId('ok')).toBeInTheDocument()
  })

  it('renders the default fallback when a child throws', () => {
    render(
      <ErrorBoundary>
        <Throws />
      </ErrorBoundary>
    )
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /refresh page/i })).toBeInTheDocument()
  })

  it('renders a custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>custom message</div>}>
        <Throws />
      </ErrorBoundary>
    )
    expect(screen.getByText('custom message')).toBeInTheDocument()
  })

  it('invokes onError with the caught error', () => {
    const onError = vi.fn()
    render(
      <ErrorBoundary onError={onError}>
        <Throws message="explode" />
      </ErrorBoundary>
    )
    expect(onError).toHaveBeenCalledTimes(1)
    const [err] = onError.mock.calls[0]
    expect(err).toBeInstanceOf(Error)
    expect(err.message).toBe('explode')
  })

  it('resets to children when Try Again is clicked', () => {
    // External flag flips so the child stops throwing on the next render -
    // this is the realistic scenario for a retry (e.g. network back, flag flipped).
    let shouldThrow = true
    function Conditional() {
      if (shouldThrow) throw new Error('temporary')
      return <div data-testid="ok">recovered</div>
    }

    render(
      <ErrorBoundary>
        <Conditional />
      </ErrorBoundary>
    )
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()

    shouldThrow = false
    fireEvent.click(screen.getByRole('button', { name: /try again/i }))

    expect(screen.getByTestId('ok')).toBeInTheDocument()
  })
})

describe('withErrorBoundary HOC', () => {
  it('wraps a component and renders fallback on throw', () => {
    const Wrapped = withErrorBoundary(Throws, <div>hoc-fallback</div>)
    render(<Wrapped />)
    expect(screen.getByText('hoc-fallback')).toBeInTheDocument()
  })

  it('renders the wrapped component normally when it does not throw', () => {
    const Wrapped = withErrorBoundary(Ok)
    render(<Wrapped />)
    expect(screen.getByTestId('ok')).toBeInTheDocument()
  })
})

describe('NetworkErrorFallback', () => {
  it('shows the message and triggers onRetry when clicked', () => {
    const onRetry = vi.fn()
    render(<NetworkErrorFallback onRetry={onRetry} />)
    expect(screen.getByText(/connection error/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /retry connection/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('omits the retry button when onRetry is not provided', () => {
    render(<NetworkErrorFallback />)
    expect(screen.queryByRole('button', { name: /retry/i })).not.toBeInTheDocument()
  })
})
