import { useState, useEffect, useCallback } from 'react'
import type { Conversation } from '../types/agent'
import { agentService } from '../services/agentService'

interface ConversationsTabProps {
  token: string
}

export default function ConversationsTab({ token }: ConversationsTabProps) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)

  // 加载会话列表 - 由于 API 需要按 agent_id 获取，这里使用模拟数据
  // 实际项目中可能需要一个新的 API 端点来获取用户所有会话
  const loadConversations = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      // 先获取所有智能体
      const agentsResponse = await agentService.getAgents(token)
      const allConversations: Conversation[] = []

      // 获取每个智能体的会话
      for (const agent of agentsResponse.items) {
        try {
          const convResponse = await agentService.getAgentConversations(token, agent.id)
          allConversations.push(...convResponse.items)
        } catch {
          // 忽略单个智能体的错误
        }
      }

      // 按更新时间排序
      allConversations.sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )

      setConversations(allConversations)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  const handleDelete = async (conversationId: number) => {
    try {
      await agentService.deleteConversation(token, conversationId)
      setConversations((prev) => prev.filter((c) => c.id !== conversationId))
      setDeleteConfirm(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) {
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    } else if (days === 1) {
      return '昨天'
    } else if (days < 7) {
      return `${days}天前`
    } else {
      return date.toLocaleDateString('zh-CN')
    }
  }

  const filteredConversations = searchQuery
    ? conversations.filter(
        (c) =>
          c.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          c.summary?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : conversations

  return (
    <div className="space-y-6">
      {/* 搜索框 */}
      <div className="relative">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="搜索会话..."
          className="w-full px-4 py-3 bg-gray-900/50 border border-cyan-500/30 rounded
                     text-gray-100 placeholder-gray-500 focus:border-cyan-500
                     focus:ring-2 focus:ring-cyan-500/20 transition-all"
        />
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">🔍</span>
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
          <div className="animate-spin text-4xl neon-text">◌</div>
          <p className="text-gray-400 mt-4">加载中...</p>
        </div>
      )}

      {/* 空状态 */}
      {!loading && filteredConversations.length === 0 && (
        <div className="cyber-card p-12 text-center">
          <div className="text-6xl mb-4 opacity-50">💬</div>
          <h3 className="text-2xl font-semibold neon-text mb-4">NO CONVERSATIONS</h3>
          <div className="h-1 w-48 mx-auto bg-gradient-to-r from-transparent via-cyan-500 to-transparent mb-6"></div>
          <p className="text-gray-400">
            {searchQuery ? '没有找到匹配的会话' : '还没有会话记录'}
          </p>
        </div>
      )}

      {/* 会话列表 */}
      {!loading && filteredConversations.length > 0 && (
        <div className="space-y-2">
          {filteredConversations.map((conversation) => (
            <div
              key={conversation.id}
              className="cyber-card p-4 hover:border-cyan-500/50 transition-all group"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="text-gray-200 font-medium truncate">
                      {conversation.title || '未命名会话'}
                    </h4>
                    <span className="text-xs text-gray-500">
                      {formatDate(conversation.updated_at)}
                    </span>
                  </div>
                  {conversation.summary && (
                    <p className="text-sm text-gray-500 truncate">{conversation.summary}</p>
                  )}
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <span className="text-cyan-400">💬</span>
                      {conversation.message_count} 条消息
                    </span>
                  </div>
                </div>

                {/* 操作按钮 */}
                <button
                  onClick={() => setDeleteConfirm(conversation.id)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity px-3 py-1.5
                             text-red-400 hover:bg-red-500/10 rounded text-sm"
                >
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 删除确认对话框 */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="cyber-card max-w-sm w-full p-6 animate-slideUp">
            <h3 className="text-xl font-bold text-red-400 mb-4">确认删除</h3>
            <p className="text-gray-400 mb-6">
              确定要删除这个会话吗？所有消息都将被删除。
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
