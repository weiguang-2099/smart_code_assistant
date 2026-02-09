import { useState, useEffect, useCallback, useMemo, memo } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { documentService } from '../services/documentService'
import type { Document, DocumentListParams } from '../types/document'
import PDFUploader from '../components/PDFUploader'

// Memoized document card component for better performance
const DocumentCard = memo(({ 
  doc, 
  onDelete 
}: { 
  doc: Document
  onDelete: (id: number) => void 
}) => {
  return (
    <div
      key={doc.id}
      className="cyber-card p-6 hover:border-cyan-500/50 transition-all group relative overflow-hidden"
    >
      {/* Hover glow effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/0 via-purple-500/0 to-pink-500/0 group-hover:from-cyan-500/5 group-hover:via-purple-500/5 group-hover:to-pink-500/5 transition-all duration-300 pointer-events-none"></div>
      
      <div className="relative z-10">
        <div className="flex items-start justify-between mb-3">
          <Link
            to={`/documents/${doc.id}`}
            className="text-xl font-semibold neon-text truncate flex-1 hover:text-cyan-400 transition-colors"
          >
            {doc.title}
          </Link>
          <div className="flex gap-1 ml-2">
            <Link
              to={`/documents/${doc.id}/edit`}
              className="text-gray-400 hover:text-cyan-400 px-2 py-1 transition-colors"
              title="Edit"
            >
              ✎
            </Link>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDelete(doc.id)
              }}
              className="text-gray-400 hover:text-red-400 px-2 py-1 transition-colors"
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
            <span className="text-xs px-3 py-1 border border-cyan-500/30 text-cyan-300 rounded-full backdrop-blur-sm bg-cyan-500/10">
              {doc.category}
            </span>
          )}
          <span className="text-xs px-3 py-1 border border-purple-500/30 text-purple-300 rounded-full backdrop-blur-sm bg-purple-500/10">
            v{doc.version_count}
          </span>
          {doc.is_published && (
            <span className="text-xs px-3 py-1 border border-green-500/30 text-green-300 rounded-full backdrop-blur-sm bg-green-500/10">
              Published
            </span>
          )}
        </div>

        <div className="flex items-center justify-between text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="text-cyan-400">◆</span>
            {new Date(doc.updated_at).toLocaleDateString()}
          </span>
        </div>
      </div>
    </div>
  )
})

DocumentCard.displayName = 'DocumentCard'

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

  // Memoized fetch function
  const fetchDocuments = useCallback(async (pageNum = 1) => {
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
  }, [isAuthenticated, token, search, category, sortBy, sortOrder])

  useEffect(() => {
    fetchDocuments()
  }, [isAuthenticated, token])

  // Debounced filter changes
  useEffect(() => {
    const timer = setTimeout(() => {
      if (isAuthenticated) {
        fetchDocuments(1)
      }
    }, 500)
    return () => clearTimeout(timer)
  }, [search, category, sortBy, sortOrder, isAuthenticated, fetchDocuments])

  // Memoized delete handler
  const handleDeleteDocument = useCallback(async (documentId: number) => {
    if (!confirm('⚠ DELETE DOCUMENT?\n\nThis action cannot be undone.')) {
      return
    }

    try {
      await documentService.deleteDocument(token!, documentId)
      fetchDocuments(page)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document')
    }
  }, [token, page, fetchDocuments])

  // Memoized pagination handlers
  const handlePrevPage = useCallback(() => {
    if (page > 1) fetchDocuments(page - 1)
  }, [page, fetchDocuments])

  const handleNextPage = useCallback(() => {
    if (page < totalPages) fetchDocuments(page + 1)
  }, [page, totalPages, fetchDocuments])

  if (!isAuthenticated) {
    return (
      <div className="text-center py-20">
        <div className="mb-6">
          <div className="text-6xl mb-4 animate-pulse">🔒</div>
          <h2 className="text-4xl font-bold neon-text mb-4 tracking-wider">ACCESS DENIED</h2>
          <div className="h-1 w-48 mx-auto bg-gradient-to-r from-transparent via-cyan-500 to-transparent mb-6"></div>
        </div>
        <p className="text-cyan-300 mb-8 text-lg">Initialize authentication protocol to proceed</p>
        <Link to="/login" className="cyber-btn">
          &gt; AUTHENTICATE &lt;
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with enhanced styling */}
      <div className="flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-cyan-400 text-2xl">◆</span>
            <h2 className="text-3xl font-bold neon-text tracking-wider">{'<DOCUMENTS />'}</h2>
          </div>
          <div className="h-1 w-32 bg-gradient-to-r from-cyan-500 via-purple-500 to-transparent"></div>
          <div className="flex items-center gap-2 text-sm mt-2">
            <span className="text-gray-500">TOTAL:</span>
            <span className="text-cyan-400 font-bold">{total}</span>
            <span className="text-gray-500">documents</span>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowUploadModal(true)}
            className="cyber-btn px-4 py-2 text-sm flex items-center gap-2"
            style={{ borderColor: 'var(--color-neon-purple)', color: 'var(--color-neon-purple)' }}
          >
            <span>📄</span>
            <span>UPLOAD PDF</span>
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="cyber-btn px-4 py-2 text-sm flex items-center gap-2"
            style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
          >
            <span>+</span>
            <span>NEW DOCUMENT</span>
          </button>
        </div>
      </div>

      {/* Enhanced Filters */}
      <div className="cyber-card p-4 backdrop-blur-md">
        <div className="flex flex-wrap gap-4">
          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-cyan-400">🔍</span>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search documents..."
                className="w-full pl-10 px-4 py-2 bg-gray-900/50 border border-cyan-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
              />
            </div>
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
        <div className="p-4 border border-red-500/50 rounded bg-red-500/10 flex justify-between items-center backdrop-blur-sm">
          <div className="flex items-center gap-2">
            <span className="text-red-400">⚠</span>
            <p className="text-sm text-red-400">{error}</p>
          </div>
          <button onClick={() => setError('')} className="text-red-400 hover:text-white transition-colors">✕</button>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block relative">
            <div className="animate-spin text-4xl neon-text">◌</div>
            <div className="absolute inset-0 animate-ping text-4xl neon-text opacity-30">◌</div>
          </div>
          <p className="text-gray-400 mt-4 tracking-wider">LOADING DOCUMENTS...</p>
        </div>
      ) : documents.length === 0 ? (
        /* Empty State */
        <div className="cyber-card p-12 text-center backdrop-blur-md">
          <div className="text-6xl mb-4 opacity-50">📄</div>
          <h3 className="text-2xl font-semibold neon-text mb-4 tracking-wider">NO DOCUMENTS DETECTED</h3>
          <div className="h-1 w-48 mx-auto bg-gradient-to-r from-transparent via-cyan-500 to-transparent mb-6"></div>
          <p className="text-gray-400 mb-8">Initialize your first document to begin</p>
          <div className="flex justify-center gap-4">
            <button
              onClick={() => setShowUploadModal(true)}
              className="cyber-btn px-6 py-3"
              style={{ borderColor: 'var(--color-neon-purple)', color: 'var(--color-neon-purple)' }}
            >
              📄 UPLOAD PDF
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="cyber-btn px-6 py-3"
              style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
            >
              + CREATE DOCUMENT
            </button>
          </div>
        </div>
      ) : (
        /* Documents Grid - Using memoized components */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {documents.map((doc) => (
            <DocumentCard key={doc.id} doc={doc} onDelete={handleDeleteDocument} />
          ))}
        </div>
      )}

      {/* Enhanced Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-4 mt-8">
          <button
            onClick={handlePrevPage}
            disabled={page === 1}
            className="cyber-btn px-4 py-2 text-sm disabled:opacity-30 disabled:cursor-not-allowed"
          >
            &lt; PREV
          </button>
          
          <div className="flex items-center gap-2 px-6 py-2 cyber-card backdrop-blur-sm">
            <span className="text-cyan-400 font-bold">{page}</span>
            <span className="text-gray-500">/</span>
            <span className="text-gray-400">{totalPages}</span>
          </div>
          
          <button
            onClick={handleNextPage}
            disabled={page === totalPages}
            className="cyber-btn px-4 py-2 text-sm disabled:opacity-30 disabled:cursor-not-allowed"
          >
            NEXT &gt;
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
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fadeIn">
      <div className="cyber-card max-w-md w-full p-8 animate-slideUp">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-2xl font-bold neon-text-purple tracking-wider">
              {'<NEW DOCUMENT />'}
            </h3>
            <div className="h-0.5 w-24 bg-gradient-to-r from-purple-500 to-transparent mt-1"></div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl transition-colors"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-purple-300 mb-2 tracking-wider">
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
            <label className="block text-sm font-medium text-purple-300 mb-2 tracking-wider">
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
            <label className="block text-sm font-medium text-purple-300 mb-2 tracking-wider">
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
              CANCEL
            </button>
            <button
              type="submit"
              disabled={creating || !title.trim()}
              className="flex-1 cyber-btn py-3 disabled:opacity-30 disabled:cursor-not-allowed"
              style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
            >
              {creating ? 'CREATING...' : 'CREATE'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
