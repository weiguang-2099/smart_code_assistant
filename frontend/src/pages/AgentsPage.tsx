import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import type { Agent, AgentCreate } from '../types/agent'
import { agentService } from '../services/agentService'
import AgentCard from '../components/AgentCard'
import CreateAgentWizard from '../components/CreateAgentWizard'
import AgentEditDialog from '../components/AgentEditDialog'

export default function AgentsPage() {
  const { token, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  // Dialog states
  const [createWizardOpen, setCreateWizardOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login')
    }
  }, [isAuthenticated, navigate])

  // Load agents
  const loadAgents = useCallback(async () => {
    if (!token) return

    setLoading(true)
    setError('')

    try {
      const response = await agentService.getAgents(token, {
        page: currentPage,
        page_size: 12,
        search: searchQuery || undefined,
      })
      setAgents(response.items)
      setTotalPages(response.total_pages)
      setTotalCount(response.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agents')
    } finally {
      setLoading(false)
    }
  }, [token, currentPage, searchQuery])

  useEffect(() => {
    loadAgents()
  }, [loadAgents])

  // Reset to first page when search changes
  useEffect(() => {
    setCurrentPage(1)
  }, [searchQuery])

  const handleCreateAgent = async (agent: Agent) => {
    setAgents((prev) => [agent, ...prev])
    setTotalCount((prev) => prev + 1)
    setCreateWizardOpen(false)
  }

  const handleChat = (id: number) => {
    navigate(`/agents/${id}/chat`)
  }

  const handleEdit = (id: number) => {
    setSelectedAgentId(id)
    setEditDialogOpen(true)
  }

  const handleDelete = async (id: number) => {
    if (!token) return

    try {
      await agentService.deleteAgent(token, id)
      setAgents((prev) => prev.filter((a) => a.id !== id))
      setTotalCount((prev) => prev - 1)
      setDeleteConfirm(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete agent')
    }
  }

  const handleEditComplete = () => {
    setEditDialogOpen(false)
    setSelectedAgentId(null)
    loadAgents()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold neon-text tracking-wider">{'<AGENTS />'}</h1>
          <p className="text-gray-400 mt-1">Manage your digital humans</p>
        </div>
        <button
          onClick={() => setCreateWizardOpen(true)}
          className="cyber-btn px-6 py-3"
          style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
        >
          <span className="mr-2">+</span>
          Create Agent
        </button>
      </div>

      {/* Search and Stats */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search agents..."
            className="w-full px-4 py-2.5 bg-gray-900/50 border border-cyan-500/30 rounded
                       text-gray-100 placeholder-gray-500 focus:border-cyan-500
                       focus:ring-2 focus:ring-cyan-500/20 transition-all"
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">
            {searchQuery ? '✕' : '🔍'}
          </span>
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
            />
          )}
        </div>
        <div className="text-sm text-gray-500">
          {totalCount} agent{totalCount !== 1 ? 's' : ''} total
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 border border-red-500/50 rounded bg-red-500/10 flex justify-between items-center">
          <p className="text-sm text-red-400">{error}</p>
          <button onClick={() => setError('')} className="text-red-400 hover:text-white">
            ×
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <div className="animate-spin text-4xl neon-text">◌</div>
          <p className="text-gray-400 mt-4">Loading agents...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && agents.length === 0 && (
        <div className="cyber-card p-12 text-center">
          <div className="text-6xl mb-4 opacity-50">🤖</div>
          <h3 className="text-2xl font-semibold neon-text mb-4">NO AGENTS FOUND</h3>
          <div className="h-1 w-48 mx-auto bg-gradient-to-r from-transparent via-cyan-500 to-transparent mb-6"></div>
          <p className="text-gray-400 mb-6">
            {searchQuery ? 'No agents match your search' : "You haven't created any agents yet"}
          </p>
          {!searchQuery && (
            <button
              onClick={() => setCreateWizardOpen(true)}
              className="cyber-btn px-6 py-3"
              style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
            >
              Create Your First Agent
            </button>
          )}
        </div>
      )}

      {/* Agents Grid */}
      {!loading && agents.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onChat={handleChat}
              onEdit={handleEdit}
              onDelete={setDeleteConfirm}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex justify-center items-center gap-2 pt-6">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="cyber-btn px-4 py-2 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            ← Prev
          </button>
          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum: number
              if (totalPages <= 5) {
                pageNum = i + 1
              } else if (currentPage <= 3) {
                pageNum = i + 1
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i
              } else {
                pageNum = currentPage - 2 + i
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`w-10 h-10 rounded text-sm transition-all ${
                    currentPage === pageNum
                      ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50'
                      : 'cyber-btn'
                  }`}
                >
                  {pageNum}
                </button>
              )
            })}
          </div>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="cyber-btn px-4 py-2 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Next →
          </button>
        </div>
      )}

      {/* Create Agent Wizard */}
      <CreateAgentWizard
        open={createWizardOpen}
        token={token || ''}
        onClose={() => setCreateWizardOpen(false)}
        onComplete={handleCreateAgent}
      />

      {/* Edit Dialog */}
      {selectedAgentId && (
        <AgentEditDialog
          open={editDialogOpen}
          token={token || ''}
          agentId={selectedAgentId}
          onClose={() => {
            setEditDialogOpen(false)
            setSelectedAgentId(null)
          }}
          onComplete={handleEditComplete}
        />
      )}

      {/* Delete Confirmation Dialog */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="cyber-card max-w-sm w-full p-6 animate-slideUp">
            <h3 className="text-xl font-bold text-red-400 mb-4">Confirm Delete</h3>
            <p className="text-gray-400 mb-6">
              Are you sure you want to delete this agent? All associated conversations and training
              data will be permanently removed.
            </p>
            <div className="flex gap-4">
              <button onClick={() => setDeleteConfirm(null)} className="flex-1 cyber-btn py-3">
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                className="flex-1 cyber-btn py-3"
                style={{ borderColor: 'var(--color-neon-pink)', color: 'var(--color-neon-pink)' }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
