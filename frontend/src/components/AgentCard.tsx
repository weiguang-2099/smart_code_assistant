import { memo } from 'react'
import type { Agent, AgentStatus } from '../types/agent'

interface AgentCardProps {
  agent: Agent
  onChat: (id: number) => void
  onEdit: (id: number) => void
  onDelete: (id: number) => void
}

// 状态颜色和标签映射
const statusConfig: Record<AgentStatus, { color: string; label: string; bgColor: string }> = {
  draft: { color: 'text-gray-400', label: '草稿', bgColor: 'bg-gray-500/20' },
  active: { color: 'text-green-400', label: '活跃', bgColor: 'bg-green-500/20' },
  inactive: { color: 'text-yellow-400', label: '停用', bgColor: 'bg-yellow-500/20' },
  training: { color: 'text-purple-400', label: '训练中', bgColor: 'bg-purple-500/20' },
}

function AgentCard({ agent, onChat, onEdit, onDelete }: AgentCardProps) {
  const status = statusConfig[agent.status] || statusConfig.draft

  return (
    <div className="cyber-card p-6 hover:border-cyan-500/50 transition-all group relative">
      {/* 背景渐变效果 */}
      <div
        className="absolute inset-0 bg-gradient-to-br from-cyan-500/0 via-purple-500/0 to-pink-500/0
                    group-hover:from-cyan-500/5 group-hover:via-purple-500/5 group-hover:to-pink-500/5
                    transition-all duration-300 pointer-events-none rounded-lg"
      />

      <div className="relative">
        {/* 头部：头像和状态 */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            {/* 头像 */}
            <div
              className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl
                          bg-gradient-to-br from-cyan-500/20 to-purple-500/20 border border-cyan-500/30"
            >
              {agent.avatar_url ? (
                <img
                  src={agent.avatar_url}
                  alt={agent.name}
                  className="w-full h-full rounded-lg object-cover"
                />
              ) : (
                <span className="text-cyan-400">🤖</span>
              )}
            </div>

            {/* 名称和领域 */}
            <div>
              <h3 className="text-lg font-semibold text-gray-100 group-hover:text-cyan-300 transition-colors">
                {agent.name}
              </h3>
              {agent.domain && (
                <span className="text-xs text-purple-400 font-mono">{agent.domain}</span>
              )}
            </div>
          </div>

          {/* 状态指示器 */}
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full ${status.bgColor}`}>
            <span
              className={`w-2 h-2 rounded-full ${status.color.replace('text-', 'bg-')} ${
                agent.status === 'active' ? 'animate-pulse' : ''
              }`}
            />
            <span className={`text-xs ${status.color}`}>{status.label}</span>
          </div>
        </div>

        {/* 描述 */}
        <p className="text-sm text-gray-400 mb-4 line-clamp-2 min-h-[40px]">
          {agent.description || '暂无描述'}
        </p>

        {/* 统计信息 */}
        <div className="flex items-center gap-4 mb-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="text-cyan-400">💬</span>
            {agent.conversation_count} 对话
          </span>
        </div>

        {/* 分隔线 */}
        <div className="h-px bg-gradient-to-r from-transparent via-gray-700 to-transparent mb-4" />

        {/* 操作按钮 */}
        <div className="flex gap-2">
          <button
            onClick={() => onChat(agent.id)}
            disabled={agent.status !== 'active'}
            className={`
              flex-1 px-3 py-2 rounded text-sm font-medium transition-all
              flex items-center justify-center gap-1.5
              ${
                agent.status === 'active'
                  ? 'bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 border border-cyan-500/30'
                  : 'bg-gray-500/10 text-gray-500 cursor-not-allowed border border-gray-500/20'
              }
            `}
          >
            <span>💬</span>
            对话
          </button>

          <button
            onClick={() => onEdit(agent.id)}
            className="
              flex-1 px-3 py-2 rounded text-sm font-medium transition-all
              bg-purple-500/20 text-purple-400 hover:bg-purple-500/30
              border border-purple-500/30
              flex items-center justify-center gap-1.5
            "
          >
            <span>✏️</span>
            编辑
          </button>

          <button
            onClick={() => onDelete(agent.id)}
            className="
              px-3 py-2 rounded text-sm font-medium transition-all
              bg-red-500/10 text-red-400 hover:bg-red-500/20
              border border-red-500/20
            "
          >
            🗑️
          </button>
        </div>
      </div>
    </div>
  )
}

// 使用 memo 优化性能
export default memo(AgentCard)
