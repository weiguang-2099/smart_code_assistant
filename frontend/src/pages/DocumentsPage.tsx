import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { documentService } from '../services/documentService'
import type { Document, DocumentListParams } from '../types/document'
import PDFUploader from '../components/PDFUploader'

export default function DocumentsPage() {
  const { isAuthenticated, token } = useAuth()
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [total, setTotal] = useState(0)

  // Filter states
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [sortBy, setSortBy] = useState('updated_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)

  const fetchDocuments = async (pageNum = 1) => {
    if (!isAuthenticated || !token) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError('')

    const params: DocumentListParams = {
      page: pageNum,
      page_size: 20,
      search: search || undefined,
      category: category || undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
    }

    try {
      const data = await documentService.getDocuments(token, params)
      setDocuments(data.items)
      setTotalPages(data.total_pages)
      setPage(data.page)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDocuments()
  }, [isAuthenticated, token])

  // Handle filter changes with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      if (isAuthenticated) {
        fetchDocuments(1)
      }
    }, 500)
    return () => clearTimeout(timer)
  }, [search, category, sortBy, sortOrder])

  const handleDeleteDocument = async (documentId: number) => {
    if (!confirm('Are you sure you want to delete this document?')) {
      return
    }

    try {
      await documentService.deleteDocument(token!, documentId)
      fetchDocuments(page)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document')
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="text-center py-20">
        <h2 className="text-4xl font-bold neon-text mb-4">ACCESS DENIED</h2>
        <p className="text-cyan-300 mb-8">Please authenticate to access your documents</p>
        <Link to="/login" className="cyber-btn">
          Initialize Session
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-3xl font-bold neon-text tracking-wider">{'<DOCUMENTS />'}</h2>
          <div className="h-px w-32 bg-gradient-to-r from-cyan-500 to-transparent mt-2"></div>
          <p className="text-gray-400 text-sm mt-2">Total: {total} documents</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowUploadModal(true)}
            className="cyber-btn px-4 py-2 text-sm"
            style={{ borderColor: 'var(--color-neon-purple)', color: 'var(--color-neon-purple)' }}
          >
            📄 Upload PDF
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="cyber-btn px-4 py-2 text-sm"
            style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
          >
            + New Document
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="cyber-card p-4">
        <div className="flex flex-wrap gap-4">
          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search documents..."
              className="w-full px-4 py-2 bg-gray-900/50 border border-cyan-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
            />
          </div>

          {/* Category */}
          <div className="w-40">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-4 py-2 bg-gray-900/50 border border-cyan-500/30 rounded text-gray-100 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
            >
              <option value="">All Categories</option>
              <option value="architecture">Architecture</option>
              <option value="api">API</option>
              <option value="tutorial">Tutorial</option>
              <option value="documentation">Documentation</option>
              <option value="notes">Notes</option>
            </select>
          </div>

          {/* Sort By */}
          <div className="w-40">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full px-4 py-2 bg-gray-900/50 border border-cyan-500/30 rounded text-gray-100 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
            >
              <option value="updated_at">Last Updated</option>
              <option value="created_at">Created</option>
              <option value="title">Title</option>
            </select>
          </div>

          {/* Sort Order */}
          <button
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            className="cyber-btn px-4 py-2 text-sm"
            title={`Sort ${sortOrder === 'asc' ? 'Descending' : 'Ascending'}`}
          >
            {sortOrder === 'asc' ? '↑' : '↓'}
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 border border-red-500/50 rounded bg-red-500/10 flex justify-between items-center">
          <p className="text-sm text-red-400">{error}</p>
          <button onClick={() => setError('')} className="text-red-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin text-4xl neon-text">◌</div>
          <p className="text-gray-400 mt-4">Loading documents...</p>
        </div>
      ) : documents.length === 0 ? (
        /* Empty State */
        <div className="cyber-card p-12 text-center">
          <div className="text-6xl mb-4">📄</div>
          <h3 className="text-2xl font-semibold neon-text mb-4">No Documents Yet</h3>
          <p className="text-gray-400 mb-8">Upload a PDF or create a new document to get started</p>
          <div className="flex justify-center gap-4">
            <button
              onClick={() => setShowUploadModal(true)}
              className="cyber-btn px-6 py-3"
              style={{ borderColor: 'var(--color-neon-purple)', color: 'var(--color-neon-purple)' }}
            >
              Upload PDF
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="cyber-btn px-6 py-3"
              style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
            >
              Create Document
            </button>
          </div>
        </div>
      ) : (
        /* Documents Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="cyber-card p-6 hover:border-cyan-500/50 transition-all float-animation"
            >
              <div className="flex items-start justify-between mb-3">
                <Link
                  to={`/documents/${doc.id}`}
                  className="text-xl font-semibold neon-text truncate flex-1 hover:text-cyan-400"
                >
                  {doc.title}
                </Link>
                <div className="flex gap-1 ml-2">
                  <Link
                    to={`/documents/${doc.id}/edit`}
                    className="text-gray-400 hover:text-cyan-400 px-2 py-1"
                    title="Edit"
                  >
                    ✎
                  </Link>
                  <button
                    onClick={() => handleDeleteDocument(doc.id)}
                    className="text-gray-400 hover:text-red-400 px-2 py-1"
                    title="Delete"
                  >
                    🗑
                  </button>
                </div>
              </div>

              {doc.description && (
                <p className="text-gray-400 text-sm mb-4 line-clamp-2">{doc.description}</p>
              )}

              <div className="flex flex-wrap gap-2 mb-4">
                {doc.category && (
                  <span className="text-xs px-2 py-1 border border-cyan-500/30 text-cyan-300 rounded">
                    {doc.category}
                  </span>
                )}
                <span className="text-xs px-2 py-1 border border-purple-500/30 text-purple-300 rounded">
                  v{doc.version_count}
                </span>
                {doc.is_published && (
                  <span className="text-xs px-2 py-1 border border-green-500/30 text-green-300 rounded">
                    Published
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>Updated: {new Date(doc.updated_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          <button
            onClick={() => fetchDocuments(page - 1)}
            disabled={page === 1}
            className="cyber-btn px-4 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-gray-400 text-sm">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => fetchDocuments(page + 1)}
            disabled={page === totalPages}
            className="cyber-btn px-4 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}

      {/* PDF Upload Modal */}
      {showUploadModal && (
        <PDFUploader
          token={token!}
          onClose={() => setShowUploadModal(false)}
          onComplete={(documentId) => {
            setShowUploadModal(false)
            fetchDocuments(1)
          }}
          onError={(err) => setError(err)}
        />
      )}

      {/* Create Document Modal */}
      {showCreateModal && (
        <CreateDocumentModal
          token={token!}
          onClose={() => setShowCreateModal(false)}
          onComplete={(documentId) => {
            setShowCreateModal(false)
            fetchDocuments(1)
          }}
          onError={(err) => setError(err)}
        />
      )}
    </div>
  )
}

// ==================== Create Document Modal ====================

interface CreateDocumentModalProps {
  token: string
  onClose: () => void
  onComplete: (documentId: number) => void
  onError: (error: string) => void
}

function CreateDocumentModal({ token, onClose, onComplete, onError }: CreateDocumentModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [creating, setCreating] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!title.trim()) {
      onError('Title is required')
      return
    }

    setCreating(true)

    try {
      const doc = await documentService.createDocument(token, {
        title: title.trim(),
        description: description.trim() || undefined,
        category: category.trim() || undefined,
      })
      onComplete(doc.id)
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to create document')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="cyber-card max-w-md w-full p-8">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-2xl font-bold neon-text-purple tracking-wider">
            {'<NEW DOCUMENT />'}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-purple-300 mb-2">
              TITLE *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
              placeholder="My Document"
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
              className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all resize-none"
              placeholder="What is this document about?"
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
              className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
            >
              <option value="">No Category</option>
              <option value="architecture">Architecture</option>
              <option value="api">API</option>
              <option value="tutorial">Tutorial</option>
              <option value="documentation">Documentation</option>
              <option value="notes">Notes</option>
            </select>
          </div>

          <div className="flex gap-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 cyber-btn py-3"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={creating || !title.trim()}
              className="flex-1 cyber-btn py-3 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
