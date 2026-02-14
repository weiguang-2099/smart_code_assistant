import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Agent } from '../types/agent'
import { agentService } from '../services/agentService'
import AgentCard from './AgentCard'
import CreateAgentWizard from './CreateAgentWizard'

interface MyAgentsTabProps {
  token: string
}

export default function MyAgentsTab({ token }: MyAgentsTabProps) {
  const navigate = useNavigate()
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateWizard, setShowCreateWizard] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)

  const loadAgents = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const response = await agentService.getAgents(token, {
        search: searchQuery || undefined,
      })
      setAgents(response.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [token, searchQuery])

  useEffect(() => {
    loadAgents()
  }, [loadAgents])

  const handleChat = (agentId: number) => {
    navigate(`/agents/${agentId}/chat`)
  }

  const handleEdit = (agentId: number) => {
    navigate(`/agents/${agentId}/edit`)
  }

  const handleDelete = async (agentId: number) => {
    try {
      await agentService.deleteAgent(token, agentId)
      setAgents((prev) => prev.filter((a) => a.id !== agentId))
      setDeleteConfirm(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
    }
  }

  const handleCreateComplete = (agent: Agent) => {
    setAgents((prev) => [agent, ...prev])
    setShowCreateWizard(false)
  }

  const filteredAgents = searchQuery
    ? agents.filter(
        (a) =>
          a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          a.domain?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : agents

  return (
    <div className="space-y-6">
      {/* 头部：搜索和创建按钮 */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索智能体..."
            className="w-full px-4 py-3 bg-gray-900/50 border border-cyan-500/30 rounded
                       text-gray-100 placeholder-gray-500 focus:border-cyan-500
                       focus:ring-2 focus:ring-cyan-500/20 transition-all"
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">🔍</span>
        </div>
        <button
          onClick={() => setShowCreateWizard(true)}
          className="cyber-btn px-6 py-3"
          style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
        >
          + 创建智能体
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="p-4 border border-red-500/50 rounded bg-red-500/10 flex justify-between items-center">
          <p className="text-sm text-red-400">{error}</p>
          <button onClick={() => setError('')} className="text-red-400 hover:text-white">
            ×
          </button>
        </div>
      )}

      {/* 加载状态 */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block relative">
            <div className="animate-spin text-4xl neon-text">◌</div>
          </div>
          <p className="text-gray-400 mt-4">加载中...</p>
        </div>
      )}

      {/* 空状态 */}
      {!loading && filteredAgents.length === 0 && (
        <div className="cyber-card p-12 text-center">
          <div className="text-6xl mb-4 opacity-50">🤖</div>
          <h3 className="text-2xl font-semibold neon-text mb-4">NO AGENTS</h3>
          <div className="h-1 w-48 mx-auto bg-gradient-to-r from-transparent via-cyan-500 to-transparent mb-6"></div>
          <p className="text-gray-400 mb-8">
            {searchQuery ? '没有找到匹配的智能体' : '还没有创建任何智能体'}
          </p>
          {!searchQuery && (
            <button
              onClick={() => setShowCreateWizard(true)}
              className="cyber-btn px-6 py-3"
              style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
            >
              创建第一个智能体
            </button>
          )}
        </div>
      )}

      {/* 智能体卡片网格 */}
      {!loading && filteredAgents.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAgents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onChat={handleChat}
              onEdit={handleEdit}
              onDelete={(id) => setDeleteConfirm(id)}
            />
          ))}
        </div>
      )}

      {/* 创建向导 */}
      <CreateAgentWizard
        open={showCreateWizard}
        token={token}
        onClose={() => setShowCreateWizard(false)}
        onComplete={handleCreateComplete}
      />

      {/* 删除确认对话框 */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="cyber-card max-w-sm w-full p-6 animate-slideUp">
            <h3 className="text-xl font-bold text-red-400 mb-4">确认删除</h3>
            <p className="text-gray-400 mb-6">
              确定要删除这个智能体吗？此操作无法撤销。
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="flex-1 cyber-btn py-3"
              >
                取消
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                className="flex-1 cyber-btn py-3"
                style={{ borderColor: 'var(--color-neon-pink)', color: 'var(--color-neon-pink)' }}
              >
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
