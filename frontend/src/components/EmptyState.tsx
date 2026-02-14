import React from 'react'
import { Link } from 'react-router-dom'

interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: {
    label: string
    onClick?: () => void
    to?: string
  }
  className?: string
}

/**
 * Empty state component for displaying when there's no content
 */
const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center py-12 px-4 text-center ${className}`}
      role="status"
      aria-label={title}
    >
      {icon && (
        <div className="mb-4 text-4xl opacity-50" aria-hidden="true">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-semibold text-gray-300 mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-gray-500 max-w-md mb-6">{description}</p>
      )}
      {action && (
        action.to ? (
          <Link
            to={action.to}
            className="cyber-btn text-sm px-4 py-2"
            style={{ borderColor: 'var(--color-neon-blue)', color: 'var(--color-neon-blue)' }}
          >
            {action.label}
          </Link>
        ) : (
          <button
            onClick={action.onClick}
            className="cyber-btn text-sm px-4 py-2"
            style={{ borderColor: 'var(--color-neon-blue)', color: 'var(--color-neon-blue)' }}
          >
            {action.label}
          </button>
        )
      )}
    </div>
  )
}

export default EmptyState

// Pre-built empty states for common scenarios

export const NoAgentsEmptyState: React.FC<{ onCreateClick?: () => void }> = ({
  onCreateClick,
}) => (
  <EmptyState
    icon={<span className="text-5xl">🤖</span>}
    title="No Agents Yet"
    description="Create your first AI agent to start building intelligent assistants for code, writing, analysis, and more."
    action={{
      label: 'Create Agent',
      onClick: onCreateClick,
    }}
  />
)

export const NoDocumentsEmptyState: React.FC<{ onCreateClick?: () => void }> = ({
  onCreateClick,
}) => (
  <EmptyState
    icon={<span className="text-5xl">📄</span>}
    title="No Documents"
    description="Start by creating a new document or uploading a PDF to parse and organize your knowledge base."
    action={{
      label: 'Create Document',
      onClick: onCreateClick,
    }}
  />
)

export const NoProjectsEmptyState: React.FC<{ onCreateClick?: () => void }> = ({
  onCreateClick,
}) => (
  <EmptyState
    icon={<span className="text-5xl">📁</span>}
    title="No Projects"
    description="Create your first project to organize your code files and start collaborating."
    action={{
      label: 'New Project',
      onClick: onCreateClick,
    }}
  />
)

export const NoFilesEmptyState: React.FC<{ onUploadClick?: () => void }> = ({
  onUploadClick,
}) => (
  <EmptyState
    icon={<span className="text-5xl">📝</span>}
    title="No Files"
    description="This project doesn't have any files yet. Upload or create files to get started."
    action={{
      label: 'Upload Files',
      onClick: onUploadClick,
    }}
  />
)

export const NoConversationsEmptyState: React.FC = () => (
  <EmptyState
    icon={<span className="text-5xl">💬</span>}
    title="No Conversations"
    description="Start a conversation with this agent to see your chat history here."
  />
)

export const NoSearchResultsEmptyState: React.FC<{ query: string; onClear?: () => void }> = ({
  query,
  onClear,
}) => (
  <EmptyState
    icon={<span className="text-5xl">🔍</span>}
    title="No Results Found"
    description={`We couldn't find anything matching "${query}". Try different keywords or clear your search.`}
    action={onClear ? {
      label: 'Clear Search',
      onClick: onClear,
    } : undefined}
  />
)

export const NoTrainingTasksEmptyState: React.FC = () => (
  <EmptyState
    icon={<span className="text-5xl">🎓</span>}
    title="No Training Tasks"
    description="This agent hasn't been trained yet. Start a training task to improve its performance."
  />
)

export const ErrorEmptyState: React.FC<{
  title?: string
  message?: string
  onRetry?: () => void
}> = ({
  title = 'Something Went Wrong',
  message = 'An error occurred while loading the data. Please try again.',
  onRetry,
}) => (
  <EmptyState
    icon={<span className="text-5xl text-red-400">⚠️</span>}
    title={title}
    description={message}
    action={onRetry ? {
      label: 'Try Again',
      onClick: onRetry,
    } : undefined}
  />
)

export const OfflineEmptyState: React.FC<{ onRetry?: () => void }> = ({
  onRetry,
}) => (
  <EmptyState
    icon={<span className="text-5xl">📡</span>}
    title="You're Offline"
    description="Please check your internet connection and try again."
    action={onRetry ? {
      label: 'Retry',
      onClick: onRetry,
    } : undefined}
  />
)

export const ComingSoonEmptyState: React.FC<{ feature?: string }> = ({
  feature = 'This feature',
}) => (
  <EmptyState
    icon={<span className="text-5xl">🚧</span>}
    title="Coming Soon"
    description={`${feature} is currently under development. Check back soon for updates!`}
  />
)
