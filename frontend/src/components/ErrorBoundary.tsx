import React, { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

/**
 * Error Boundary component to catch JavaScript errors in child components
 */
class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo })

    // Log error to console in development
    console.error('Error caught by boundary:', error, errorInfo)

    // Call optional error handler
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
  }

  handleReload = (): void => {
    window.location.reload()
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Default error UI
      return (
        <div className="min-h-[400px] flex items-center justify-center p-4">
          <div className="cyber-card p-8 max-w-lg w-full text-center">
            <div className="text-6xl mb-4" role="img" aria-label="Error">
              💥
            </div>
            <h2 className="text-2xl font-bold text-red-400 mb-2 neon-text" style={{ textShadow: '0 0 10px rgba(255, 100, 100, 0.5)' }}>
              Something Went Wrong
            </h2>
            <p className="text-gray-400 mb-6">
              An unexpected error occurred. Please try refreshing the page or contact support if the problem persists.
            </p>

            {/* Error details (development only) */}
            {import.meta.env.DEV && this.state.error && (
              <div className="mb-6 p-4 bg-red-900/20 border border-red-500/30 rounded text-left overflow-auto max-h-40">
                <p className="text-red-400 text-sm font-mono break-all">
                  {this.state.error.toString()}
                </p>
                {this.state.errorInfo && (
                  <pre className="text-red-300/70 text-xs mt-2 whitespace-pre-wrap">
                    {this.state.errorInfo.componentStack}
                  </pre>
                )}
              </div>
            )}

            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="cyber-btn px-4 py-2 text-sm"
                style={{ borderColor: 'var(--color-neon-blue)', color: 'var(--color-neon-blue)' }}
              >
                Try Again
              </button>
              <button
                onClick={this.handleReload}
                className="cyber-btn px-4 py-2 text-sm"
                style={{ borderColor: 'var(--color-neon-purple)', color: 'var(--color-neon-purple)' }}
              >
                Refresh Page
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary

/**
 * Higher-order component to wrap a component with an error boundary
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  fallback?: ReactNode,
  onError?: (error: Error, errorInfo: ErrorInfo) => void
): React.FC<P> {
  return function WithErrorBoundaryWrapper(props: P) {
    return (
      <ErrorBoundary fallback={fallback} onError={onError}>
        <WrappedComponent {...props} />
      </ErrorBoundary>
    )
  }
}

/**
 * Hook for imperatively triggering an error boundary
 */
export function useErrorBoundary(): (error: Error) => void {
  const [, setError] = React.useState<Error | null>(null)

  return (error: Error) => {
    setError(() => {
      throw error
    })
  }
}

/**
 * Network error fallback component
 */
export const NetworkErrorFallback: React.FC<{ onRetry?: () => void }> = ({
  onRetry,
}) => (
  <div className="cyber-card p-8 text-center">
    <div className="text-5xl mb-4">📡</div>
    <h3 className="text-lg font-semibold text-yellow-400 mb-2">Connection Error</h3>
    <p className="text-gray-400 mb-4">
      Unable to connect to the server. Please check your internet connection.
    </p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="cyber-btn px-4 py-2 text-sm"
        style={{ borderColor: 'var(--color-neon-blue)', color: 'var(--color-neon-blue)' }}
      >
        Retry Connection
      </button>
    )}
  </div>
)
