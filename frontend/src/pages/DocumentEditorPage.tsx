import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { DocumentProvider, useDocument } from '../contexts/DocumentContext'
import TipTapEditor from '../components/TipTapEditor'
import VersionHistory from '../components/VersionHistory'
import VersionDiff from '../components/VersionDiff'
import { markdownToTipTap, tipTapToMarkdown } from '../utils/formatConverter'

function DocumentEditorContent() {
  const { documentId } = useParams<{ documentId: string }>()
  const navigate = useNavigate()
  const { token } = useAuth()
  const {
    document,
    loading,
    error,
    currentContent,
    hasUnsavedChanges,
    versions,
    viewingVersionId,
    comparingVersions,
    comparisonResult,
    loadDocument,
    saveContent,
    rollbackVersion,
    viewVersion,
    compareVersions,
    closeComparison,
    clearDocument,
    updateMetadata,
    setCurrentContent,
  } = useDocument()

  const [showMetadataModal, setShowMetadataModal] = useState(false)
  const [showVersionHistory, setShowVersionHistory] = useState(false)
  const [saveSummary, setSaveSummary] = useState('')
  const [showSaveSummary, setShowSaveSummary] = useState(false)

  // Load document on mount
  useEffect(() => {
    if (documentId && token) {
      loadDocument(parseInt(documentId))
    }

    return () => {
      clearDocument()
    }
  }, [documentId, token])

  // Warn before leaving with unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = ''
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasUnsavedChanges])

  const handleSave = async () => {
    if (!currentContent) return

    try {
      const markdown = tipTapToMarkdown(currentContent)
      await saveContent(markdown, currentContent, saveSummary || undefined)
      setShowSaveSummary(false)
      setSaveSummary('')
    } catch (err) {
      // Error is handled by context
    }
  }

  const handleContentChange = (tiptap: any, markdown: string) => {
    setCurrentContent(tiptap)
  }

  if (loading) {
    return (
      <div className="text-center py-20">
        <div className="animate-spin text-4xl neon-text">◌</div>
        <p className="text-gray-400 mt-4">Loading document...</p>
      </div>
    )
  }

  if (error && !document) {
    return (
      <div className="text-center py-20">
        <h2 className="text-4xl font-bold text-red-400 mb-4">Error</h2>
        <p className="text-gray-400 mb-8">{error}</p>
        <Link to="/documents" className="cyber-btn">
          Back to Documents
        </Link>
      </div>
    )
  }

  if (!document) {
    return (
      <div className="text-center py-20">
        <h2 className="text-4xl font-bold text-gray-400 mb-4">Document Not Found</h2>
        <Link to="/documents" className="cyber-btn">
          Back to Documents
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap justify-between items-start gap-4">
        <div className="flex items-center gap-4">
          <Link
            to="/documents"
            className="cyber-btn px-3 py-2 text-sm"
            title="Back to documents"
          >
            ←
          </Link>
          <div>
            <h1 className="text-2xl font-bold neon-text">{document.title}</h1>
                <div className="flex items-center gap-3 text-sm text-gray-400 mt-1">
                  <span>v{document.version_count} versions</span>
                  {document.category && (
                    <span className="px-2 py-0.5 border border-purple-500/30 text-purple-300 rounded text-xs">
                      {document.category}
                    </span>
                  )}
                  {viewingVersionId && (
                    <span className="text-yellow-400">
                      Viewing version {viewingVersionId}
                    </span>
                  )}
                  {hasUnsavedChanges && (
                    <span className="text-orange-400">Unsaved changes</span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowVersionHistory(true)}
                className="cyber-btn px-4 py-2 text-sm"
                title="View version history"
              >
                📜 History
              </button>

              <button
                onClick={() => setShowMetadataModal(true)}
                className="cyber-btn px-4 py-2 text-sm"
                title="Edit document metadata"
              >
                ⚙ Settings
              </button>

              <button
                onClick={() => setShowSaveSummary(true)}
                disabled={!hasUnsavedChanges}
                className="cyber-btn px-4 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  borderColor: hasUnsavedChanges ? 'var(--color-neon-green)' : undefined,
                  color: hasUnsavedChanges ? 'var(--color-neon-green)' : undefined,
                }}
              >
                {hasUnsavedChanges ? '💾 Save Changes' : 'Saved'}
              </button>
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="p-4 border border-red-500/50 rounded bg-red-500/10 flex justify-between items-center">
              <p className="text-sm text-red-400">{error}</p>
              <button onClick={() => {/* Clear error via context */}} className="text-red-400 hover:text-white">
                ✕
              </button>
            </div>
          )}

          {/* Editor */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Main Editor */}
            <div className="lg:col-span-3">
              <TipTapEditor
                content={currentContent || { type: 'doc', content: [] }}
                placeholder="Start writing your document..."
                editable={true}
                onChange={handleContentChange}
              />
            </div>

            {/* Sidebar */}
            <div className="lg:col-span-1 space-y-6">
              {/* Document Info */}
              <div className="cyber-card p-4">
                <h3 className="text-sm font-semibold text-gray-400 mb-3">DOCUMENT INFO</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Created</span>
                    <span className="text-gray-300">
                      {new Date(document.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Updated</span>
                    <span className="text-gray-300">
                      {new Date(document.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Versions</span>
                    <span className="text-cyan-400">{document.version_count}</span>
                  </div>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="cyber-card p-4">
                <h3 className="text-sm font-semibold text-gray-400 mb-3">QUICK ACTIONS</h3>
                <div className="space-y-2">
                  <button
                    onClick={() => setShowVersionHistory(true)}
                    className="w-full cyber-btn px-3 py-2 text-sm text-left"
                  >
                    📜 View All Versions
                  </button>
                  <button
                    onClick={() => setShowMetadataModal(true)}
                    className="w-full cyber-btn px-3 py-2 text-sm text-left"
                  >
                    ⚙ Edit Metadata
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Version History Modal */}
          {showVersionHistory && (
            <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-40 p-4">
              <div className="cyber-card max-w-2xl w-full">
                <div className="flex justify-between items-center p-4 border-b border-gray-700">
                  <h3 className="text-lg font-semibold neon-text-purple">Version History</h3>
                  <button
                    onClick={() => setShowVersionHistory(false)}
                    className="text-gray-400 hover:text-white text-2xl"
                  >
                    ×
                  </button>
                </div>
                <div className="p-4">
                  <VersionHistory
                    documentId={document.id}
                    versions={versions}
                    currentVersionId={document.current_version_id}
                    onViewVersion={async (id) => {
                      await viewVersion(id)
                      setShowVersionHistory(false)
                    }}
                    onRollback={async (id, summary) => {
                      await rollbackVersion(id, summary)
                      setShowVersionHistory(false)
                    }}
                    onCompare={async (from, to) => {
                      await compareVersions(from, to)
                      setShowVersionHistory(false)
                    }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Version Comparison Modal */}
          {comparisonResult && (
            <VersionDiff
              comparison={comparisonResult}
              onClose={closeComparison}
            />
          )}

          {/* Save Summary Modal */}
          {showSaveSummary && (
            <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
              <div className="cyber-card max-w-md w-full p-6">
                <h3 className="text-xl font-bold neon-text-purple mb-4">Save Changes</h3>
                <p className="text-gray-400 mb-4">
                  Describe the changes you made (optional):
                </p>
                <input
                  type="text"
                  value={saveSummary}
                  onChange={(e) => setSaveSummary(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all mb-4"
                  placeholder="e.g., Fixed typo in introduction"
                  autoFocus
                />
                <div className="flex gap-3">
                  <button
                    onClick={() => {
                      setShowSaveSummary(false)
                      setSaveSummary('')
                    }}
                    className="flex-1 cyber-btn py-2"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    className="flex-1 cyber-btn py-2"
                    style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
                  >
                    Save
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Metadata Modal */}
          {showMetadataModal && (
            <MetadataModal
              document={document}
              onClose={() => setShowMetadataModal(false)}
              onSave={async (data) => {
                await updateMetadata(data)
                setShowMetadataModal(false)
              }}
            />
          )}
        </div>
      )
}

// ==================== Metadata Modal ====================

interface MetadataModalProps {
  document: any
  onClose: () => void
  onSave: (data: { title?: string; description?: string; category?: string }) => Promise<void>
}

function MetadataModal({ document, onClose, onSave }: MetadataModalProps) {
  const [title, setTitle] = useState(document.title)
  const [description, setDescription] = useState(document.description || '')
  const [category, setCategory] = useState(document.category || '')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave({
        title: title.trim(),
        description: description.trim() || undefined,
        category: category.trim() || undefined,
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="cyber-card max-w-md w-full p-6">
        <h3 className="text-xl font-bold neon-text-purple mb-4">Document Settings</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-purple-300 mb-2">
              TITLE *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-4 py-2 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-purple-300 mb-2">
              DESCRIPTION
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-2 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all resize-none"
              rows={3}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-purple-300 mb-2">
              CATEGORY
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-4 py-2 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
            >
              <option value="">No Category</option>
              <option value="architecture">Architecture</option>
              <option value="api">API</option>
              <option value="tutorial">Tutorial</option>
              <option value="documentation">Documentation</option>
              <option value="notes">Notes</option>
            </select>
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            disabled={saving}
            className="flex-1 cyber-btn py-2"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !title.trim()}
            className="flex-1 cyber-btn py-2 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ==================== Main Page Wrapper ====================

export default function DocumentEditorPage() {
  const { token, isAuthenticated } = useAuth()

  if (!isAuthenticated || !token) {
    return (
      <div className="text-center py-20">
        <h2 className="text-4xl font-bold neon-text mb-4">ACCESS DENIED</h2>
        <p className="text-cyan-300 mb-8">Please authenticate to edit documents</p>
      </div>
    )
  }

  return (
    <DocumentProvider token={token}>
      <DocumentEditorContent />
    </DocumentProvider>
  )
}
