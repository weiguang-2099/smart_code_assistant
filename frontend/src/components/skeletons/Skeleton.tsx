import React from 'react'

interface SkeletonProps {
  className?: string
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded'
  width?: string | number
  height?: string | number
  animation?: 'pulse' | 'wave' | 'none'
}

/**
 * Base Skeleton component for loading states
 */
const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'text',
  width,
  height,
  animation = 'pulse',
}) => {
  const baseClasses = 'bg-gray-700/50'

  const variantClasses = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: '',
    rounded: 'rounded-lg',
  }

  const animationClasses = {
    pulse: 'animate-pulse',
    wave: 'skeleton-wave',
    none: '',
  }

  const style: React.CSSProperties = {
    width: width || (variant === 'text' ? '100%' : undefined),
    height: height || (variant === 'text' ? '1rem' : undefined),
  }

  return (
    <div
      className={`${baseClasses} ${variantClasses[variant]} ${animationClasses[animation]} ${className}`}
      style={style}
      aria-hidden="true"
    />
  )
}

export default Skeleton

// Text skeleton with multiple lines
export const SkeletonText: React.FC<{ lines?: number; className?: string }> = ({
  lines = 3,
  className = '',
}) => {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          variant="text"
          height="0.875rem"
          width={i === lines - 1 ? '70%' : '100%'}
        />
      ))}
    </div>
  )
}

// Avatar skeleton
export const SkeletonAvatar: React.FC<{ size?: 'sm' | 'md' | 'lg' }> = ({
  size = 'md',
}) => {
  const sizeMap = {
    sm: '2rem',
    md: '3rem',
    lg: '4rem',
  }

  return (
    <Skeleton
      variant="circular"
      width={sizeMap[size]}
      height={sizeMap[size]}
    />
  )
}

// Card skeleton
export const SkeletonCard: React.FC<{ className?: string }> = ({
  className = '',
}) => {
  return (
    <div
      className={`cyber-card p-4 space-y-4 ${className}`}
      aria-hidden="true"
    >
      <div className="flex items-center gap-3">
        <SkeletonAvatar size="md" />
        <div className="flex-1 space-y-2">
          <Skeleton variant="text" height="1rem" width="60%" />
          <Skeleton variant="text" height="0.75rem" width="40%" />
        </div>
      </div>
      <SkeletonText lines={2} />
      <div className="flex gap-2">
        <Skeleton variant="rounded" height="2rem" width="4rem" />
        <Skeleton variant="rounded" height="2rem" width="4rem" />
      </div>
    </div>
  )
}

// List item skeleton
export const SkeletonListItem: React.FC<{ className?: string }> = ({
  className = '',
}) => {
  return (
    <div className={`flex items-center gap-3 p-3 ${className}`} aria-hidden="true">
      <Skeleton variant="rounded" width="2.5rem" height="2.5rem" />
      <div className="flex-1 space-y-2">
        <Skeleton variant="text" height="1rem" width="50%" />
        <Skeleton variant="text" height="0.75rem" width="30%" />
      </div>
      <Skeleton variant="rounded" width="5rem" height="1.5rem" />
    </div>
  )
}

// Table row skeleton
export const SkeletonTableRow: React.FC<{ columns?: number }> = ({
  columns = 4,
}) => {
  return (
    <tr className="border-b border-gray-700/50" aria-hidden="true">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="p-3">
          <Skeleton variant="text" height="1rem" width={i === 0 ? '60%' : '80%'} />
        </td>
      ))}
    </tr>
  )
}
