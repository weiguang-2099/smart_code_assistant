import React from 'react'
import Skeleton, { SkeletonCard, SkeletonListItem } from './Skeleton'

/**
 * Agent card skeleton for AgentsPage
 */
export const AgentCardSkeleton: React.FC = () => {
  return (
    <div className="cyber-card p-5" aria-hidden="true">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <Skeleton variant="circular" width="3rem" height="3rem" />
          <div className="space-y-2">
            <Skeleton variant="text" height="1.125rem" width="8rem" />
            <Skeleton variant="text" height="0.75rem" width="5rem" />
          </div>
        </div>
        <Skeleton variant="rounded" width="4rem" height="1.5rem" />
      </div>

      {/* Description */}
      <div className="space-y-2 mb-4">
        <Skeleton variant="text" height="0.875rem" />
        <Skeleton variant="text" height="0.875rem" width="80%" />
      </div>

      {/* Domain badge */}
      <div className="flex gap-2 mb-4">
        <Skeleton variant="rounded" width="4rem" height="1.5rem" />
        <Skeleton variant="rounded" width="3rem" height="1.5rem" />
      </div>

      {/* Stats */}
      <div className="flex items-center gap-4 pt-3 border-t border-gray-700/50">
        <Skeleton variant="text" height="0.875rem" width="5rem" />
        <Skeleton variant="text" height="0.875rem" width="5rem" />
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-4">
        <Skeleton variant="rounded" height="2rem" className="flex-1" />
        <Skeleton variant="rounded" width="2.5rem" height="2rem" />
      </div>
    </div>
  )
}

/**
 * Agent list skeleton
 */
export const AgentListSkeleton: React.FC<{ count?: number }> = ({ count = 4 }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <AgentCardSkeleton key={i} />
      ))}
    </div>
  )
}

/**
 * Document card skeleton
 */
export const DocumentCardSkeleton: React.FC = () => {
  return (
    <div className="cyber-card p-4 cursor-pointer" aria-hidden="true">
      <div className="flex items-start gap-3">
        <Skeleton variant="rounded" width="2.5rem" height="2.5rem" />
        <div className="flex-1 min-w-0">
          <Skeleton variant="text" height="1rem" width="80%" className="mb-1" />
          <Skeleton variant="text" height="0.75rem" width="50%" className="mb-2" />
          <div className="flex items-center gap-2">
            <Skeleton variant="rounded" width="3rem" height="1rem" />
            <Skeleton variant="text" height="0.75rem" width="4rem" />
          </div>
        </div>
      </div>
      <div className="mt-3 pt-3 border-t border-gray-700/30 flex items-center justify-between">
        <Skeleton variant="text" height="0.75rem" width="5rem" />
        <div className="flex gap-1">
          <Skeleton variant="circular" width="1.5rem" height="1.5rem" />
          <Skeleton variant="circular" width="1.5rem" height="1.5rem" />
        </div>
      </div>
    </div>
  )
}

/**
 * Document list skeleton
 */
export const DocumentListSkeleton: React.FC<{ count?: number }> = ({ count = 6 }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <DocumentCardSkeleton key={i} />
      ))}
    </div>
  )
}

/**
 * Project card skeleton
 */
export const ProjectCardSkeleton: React.FC = () => {
  return (
    <div className="cyber-card p-5" aria-hidden="true">
      <div className="flex items-start justify-between mb-3">
        <Skeleton variant="text" height="1.125rem" width="60%" />
        <Skeleton variant="rounded" width="4rem" height="1.5rem" />
      </div>
      <div className="space-y-2 mb-4">
        <Skeleton variant="text" height="0.875rem" />
        <Skeleton variant="text" height="0.875rem" width="70%" />
      </div>
      <div className="flex items-center justify-between pt-3 border-t border-gray-700/50">
        <div className="flex items-center gap-2">
          <Skeleton variant="circular" width="1.25rem" height="1.25rem" />
          <Skeleton variant="text" height="0.875rem" width="4rem" />
        </div>
        <Skeleton variant="text" height="0.75rem" width="5rem" />
      </div>
    </div>
  )
}

/**
 * Project list skeleton
 */
export const ProjectListSkeleton: React.FC<{ count?: number }> = ({ count = 4 }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <ProjectCardSkeleton key={i} />
      ))}
    </div>
  )
}

/**
 * File list skeleton for EditorPage
 */
export const FileListSkeleton: React.FC<{ count?: number }> = ({ count = 5 }) => {
  return (
    <div className="space-y-1" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonListItem key={i} />
      ))}
    </div>
  )
}

/**
 * Form skeleton for settings/profile
 */
export const FormSkeleton: React.FC<{ fields?: number }> = ({ fields = 4 }) => {
  return (
    <div className="space-y-6" aria-hidden="true">
      {Array.from({ length: fields }).map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton variant="text" height="0.875rem" width="6rem" />
          <Skeleton variant="rounded" height="2.75rem" />
        </div>
      ))}
      <div className="flex gap-3 pt-4">
        <Skeleton variant="rounded" height="2.5rem" width="6rem" />
        <Skeleton variant="rounded" height="2.5rem" width="6rem" />
      </div>
    </div>
  )
}

/**
 * Profile page skeleton
 */
export const ProfileSkeleton: React.FC = () => {
  return (
    <div className="flex flex-col md:flex-row gap-6" aria-hidden="true">
      {/* Sidebar */}
      <div className="w-full md:w-64 space-y-4">
        <div className="cyber-card p-4 text-center">
          <Skeleton variant="circular" width="6rem" height="6rem" className="mx-auto mb-3" />
          <Skeleton variant="text" height="1.25rem" width="60%" className="mx-auto mb-2" />
          <Skeleton variant="text" height="0.875rem" width="80%" className="mx-auto" />
        </div>
        <div className="cyber-card p-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonListItem key={i} />
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 cyber-card p-6">
        <FormSkeleton fields={5} />
      </div>
    </div>
  )
}

/**
 * Stats card skeleton
 */
export const StatCardSkeleton: React.FC = () => {
  return (
    <div className="cyber-card p-4" aria-hidden="true">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton variant="text" height="0.75rem" width="4rem" />
          <Skeleton variant="text" height="1.5rem" width="3rem" />
        </div>
        <Skeleton variant="circular" width="2.5rem" height="2.5rem" />
      </div>
    </div>
  )
}

/**
 * Conversation list skeleton
 */
export const ConversationListSkeleton: React.FC<{ count?: number }> = ({ count = 4 }) => {
  return (
    <div className="space-y-2" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="cyber-card p-3">
          <div className="flex items-center gap-3">
            <Skeleton variant="circular" width="2rem" height="2rem" />
            <div className="flex-1 space-y-1">
              <Skeleton variant="text" height="0.875rem" width="60%" />
              <Skeleton variant="text" height="0.75rem" width="40%" />
            </div>
            <Skeleton variant="text" height="0.625rem" width="3rem" />
          </div>
        </div>
      ))}
    </div>
  )
}
