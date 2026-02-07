import { useState } from 'react'
import type { VersionListItem } from '../types/document'

interface VersionHistoryProps {
  documentId: number
  versions: VersionListItem[]
  currentVersionId: number | null
  onViewVersion: (versionId: number) => void
  onRollback: (versionId: number, summary?: string) => void
  onCompare?: (fromVersion: number, toVersion: number) => void
}

export default function VersionHistory({
  documentId,
  versions,
  currentVersionId,
  onViewVersion,
  onRollback,
  onCompare,
}: VersionHistoryProps) {
  const [selectedVersions, setSelectedVersions] = useState<number[]>([])
  const [showRollbackModal, setShowRollbackModal] = useState(false)
  const [rollbackVersion, setRollbackVersion] = useState<VersionListItem | null>(null)
  const [rollbackSummary, setRollbackSummary] = useState('')

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getSourceTypeLabel = (sourceType: string) => {
    const labels: Record<string, string> = {
      upload: '📁 Upload',
      manual: '✎ Manual',
      parsed: '🔄 Parsed',
    }
    return labels[sourceType] || sourceType
  }

  const handleSelectVersion = (versionId: number) => {
    if (selectedVersions.includes(versionId)) {
      setSelectedVersions(selectedVersions.filter((id) => id !== versionId))
    } else if (selectedVersions.length < 2) {
      setSelectedVersions([...selectedVersions, versionId])
    }
  }

  const handleCompare = () => {
    if (selectedVersions.length === 2 && onCompare) {
      onCompare(selectedVersions[0], selectedVersions[1])
      setSelectedVersions([])
    }
  }

  const handleRollbackClick = (version: VersionListItem) => {
    setRollbackVersion(version)
    setRollbackSummary(`Rollback to version ${version.version_number}`)
    setShowRollbackModal(true)
  }

  const handleConfirmRollback = () => {
    if (rollbackVersion) {
      onRollback(rollbackVersion.id, rollbackSummary || undefined)
      setShowRollbackModal(false)
      setRollbackVersion(null)
      setRollbackSummary('')
    }
  }

  return (
    <>
      <div className="cyber-card">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="text-lg font-semibold neon-text-purple">Version History</h3>
          <div className="flex items-center gap-2">
            {selectedVersions.length === 2 && onCompare && (
              <button
                onClick={handleCompare}
                className="cyber-btn px-3 py-1 text-sm"
                style={{ borderColor: 'var(--color-neon-purple)', color: 'var(--color-neon-purple)' }}
              >
                Compare Selected
              </button>
            )}
            <span className="text-sm text-gray-400">{versions.length} versions</span>
          </div>
        </div>

        {/* Version List */}
        <div className="max-h-96 overflow-y-auto">
          {versions.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No versions yet
            </div>
          ) : (
            <div className="divide-y divide-gray-800">
              {versions.map((version, index) => (
                <div
                  key={version.id}
                  className={`
                    p-4 hover:bg-gray-800/30 transition-colors
                    ${currentVersionId === version.id ? 'bg-cyan-500/10 border-l-2 border-cyan-500' : ''}
                  `}
                >
                  <div className="flex items-start justify-between gap-4">
                    {/* Version Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-cyan-400">
                          v{version.version_number}
                        </span>
                        {currentVersionId === version.id && (
                          <span className="text-xs px-2 py-0.5 bg-cyan-500/20 text-cyan-400 rounded">
                            Current
                          </span>
                        )}
                        <span className="text-xs text-gray-500">
                          {getSourceTypeLabel(version.source_type)}
                        </span>
                      </div>

                      {version.change_summary && (
                        <p className="text-sm text-gray-300 mb-2 line-clamp-2">
                          {version.change_summary}
                        </p>
                      )}

                      <div className="flex items-center gap-3 text-xs text-gray-500">
                        <span>{formatDate(version.created_at)}</span>
                        {version.created_by_username && (
                          <span>by {version.created_by_username}</span>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1">
                      {onCompare && (
                        <button
                          onClick={() => handleSelectVersion(version.id)}
                          className={`
                            p-2 rounded transition-all text-sm
                            ${selectedVersions.includes(version.id)
                              ? 'bg-purple-500/30 text-purple-400 border border-purple-500/50'
                              : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                            }
                          `}
                          title={selectedVersions.includes(version.id) ? 'Deselect' : 'Select for compare'}
                        >
                          {selectedVersions.includes(version.id) ? '✓' : '☐'}
                        </button>
                      )}

                      <button
                        onClick={() => onViewVersion(version.id)}
                        className="p-2 text-gray-400 hover:text-cyan-400 hover:bg-gray-800/50 rounded transition-all text-sm"
                        title="View this version"
                      >
                        👁
                      </button>

                      {index > 0 && (
                        <button
                          onClick={() => handleRollbackClick(version)}
                          className="p-2 text-gray-400 hover:text-yellow-400 hover:bg-gray-800/50 rounded transition-all text-sm"
                          title="Rollback to this version"
                        >
                          ↺
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Rollback Confirmation Modal */}
      {showRollbackModal && rollbackVersion && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="cyber-card max-w-md w-full p-6">
            <h3 className="text-xl font-bold neon-text-purple mb-4">
              Confirm Rollback
            </h3>

            <div className="space-y-4">
              <p className="text-gray-300">
                Are you sure you want to rollback to version{' '}
                <span className="text-cyan-400 font-semibold">v{rollbackVersion.version_number}</span>?
              </p>

              {rollbackVersion.change_summary && (
                <div className="p-3 bg-gray-800/50 rounded border border-gray-700">
                  <p className="text-sm text-gray-400 mb-1">Original summary:</p>
                  <p className="text-sm text-gray-300">{rollbackVersion.change_summary}</p>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-purple-300 mb-2">
                  Change Summary (optional)
                </label>
                <input
                  type="text"
                  value={rollbackSummary}
                  onChange={(e) => setRollbackSummary(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
                  placeholder="Describe this rollback..."
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => {
                    setShowRollbackModal(false)
                    setRollbackVersion(null)
                    setRollbackSummary('')
                  }}
                  className="flex-1 cyber-btn py-2"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmRollback}
                  className="flex-1 cyber-btn py-2"
                  style={{ borderColor: 'var(--color-neon-yellow)', color: 'var(--color-neon-yellow)' }}
                >
                  Rollback
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
