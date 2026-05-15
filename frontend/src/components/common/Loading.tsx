/**
 * Loading - Loading indicator components for lazy-loaded routes
 */
import React from 'react'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  className = '',
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  }

  return (
    <div
      className={`animate-spin rounded-full border-2 border-cyan-500/30 border-t-cyan-500 ${sizeClasses[size]} ${className}`}
    />
  )
}

interface LoadingPageProps {
  message?: string
}

export const LoadingPage: React.FC<LoadingPageProps> = ({
  message = 'Loading...',
}) => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <LoadingSpinner size="lg" />
      <p className="text-gray-400 text-sm animate-pulse">{message}</p>
    </div>
  )
}

interface SkeletonProps {
  className?: string
  variant?: 'text' | 'rectangular' | 'circular'
  width?: string | number
  height?: string | number
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'rectangular',
  width,
  height,
}) => {
  const variantClasses = {
    text: 'rounded',
    rectangular: 'rounded-lg',
    circular: 'rounded-full',
  }

  const style: React.CSSProperties = {
    width: width || '100%',
    height: height || (variant === 'text' ? '1em' : '100%'),
  }

  return (
    <div
      className={`bg-gray-700/50 animate-pulse ${variantClasses[variant]} ${className}`}
      style={style}
    />
  )
}

interface SkeletonCardProps {
  lines?: number
}

export const SkeletonCard: React.FC<SkeletonCardProps> = ({ lines = 3 }) => {
  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 space-y-3">
      <Skeleton height={24} width="60%" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} height={16} width={i === lines - 1 ? '40%' : '100%'} />
      ))}
    </div>
  )
}

interface SkeletonListProps {
  count?: number
}

export const SkeletonList: React.FC<SkeletonListProps> = ({ count = 5 }) => {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} lines={2} />
      ))}
    </div>
  )
}

export default LoadingPage
