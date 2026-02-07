import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { userService } from '../services/userService'
import { documentService } from '../services/documentService'
import type { UserStats } from '../types/user'

interface ContentManagementTabProps {
  token: string
}

export default function ContentManagementTab({ token }: ContentManagementTabProps) {
  const [stats, setStats] = useState<UserStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadStats()
  }, [token])

  const loadStats = async () => {
    setLoading(true)
    setError('')

    try {
      const data = await userService.getUserStats(token)
      setStats(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stats')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin text-2xl neon-text">◌</div>
        <p className="text-gray-400 mt-2">Loading content stats...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Error Message */}
      {error && (
        <div className="p-4 border border-red-500/50 rounded bg-red-500/10 flex justify-between items-center">
          <p className="text-sm text-red-400">{error}</p>
          <button onClick={() => setError('')} className="text-red-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Stats Overview */}
      <div>
        <h3 className="text-lg font-semibold text-purple-400 mb-4">Content Overview</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatItem
            label="Documents"
            value={stats?.documents_count || 0}
            icon="📄"
            link="/documents"
          />
          <StatItem
            label="Total Versions"
            value={stats?.total_versions || 0}
            icon="📝"
          />
          <StatItem
            label="Projects"
            value={stats?.projects_count || 0}
            icon="📁"
            link="/projects"
          />
          <StatItem
            label="Storage Used"
            value={formatStorage(stats?.storage_used || 0)}
            icon="💾"
          />
        </div>
      </div>

      {/* Quick Links */}
      <div>
        <h3 className="text-lg font-semibold text-purple-400 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <QuickLinkCard
            title="Create Document"
            description="Start a new document or upload a PDF"
            icon="📄"
            link="/documents"
            color="cyan"
          />
          <QuickLinkCard
            title="Create Project"
            description="Create a new code project"
            icon="📁"
            link="/projects"
            color="purple"
          />
          <QuickLinkCard
            title="View All Content"
            description="Browse all your documents and projects"
            icon="🔍"
            link="/documents"
            color="green"
          />
        </div>
      </div>

      {/* Recent Activity Placeholder */}
      <div>
        <h3 className="text-lg font-semibold text-purple-400 mb-4">Recent Activity</h3>
        <div className="cyber-card p-8 text-center text-gray-400">
          <p>Recent activity will be displayed here</p>
          <p className="text-sm mt-2">Track your latest edits and uploads</p>
        </div>
      </div>
    </div>
  )
}

function StatItem({
  label,
  value,
  icon,
  link
}: {
  label: string
  value: string | number
  icon: string
  link?: string
}) {
  const content = (
    <>
      <div className="text-3xl mb-2">{icon}</div>
      <div className="text-2xl font-bold text-cyan-400">{value}</div>
      <div className="text-sm text-gray-400">{label}</div>
    </>
  )

  return (
    <div className="cyber-card p-4 text-center">
      {link ? (
        <Link to={link} className="block hover:scale-105 transition-transform">
          {content}
        </Link>
      ) : (
        content
      )}
    </div>
  )
}

function QuickLinkCard({
  title,
  description,
  icon,
  link,
  color
}: {
  title: string
  description: string
  icon: string
  link: string
  color: 'cyan' | 'purple' | 'green'
}) {
  const colorStyles = {
    cyan: 'hover:border-cyan-400',
    purple: 'hover:border-purple-400',
    green: 'hover:border-green-400',
  }

  return (
    <Link
      to={link}
      className={`cyber-card p-6 transition-all ${colorStyles[color]} hover:scale-105`}
    >
      <div className="text-4xl mb-3">{icon}</div>
      <h4 className="text-lg font-semibold text-gray-200 mb-2">{title}</h4>
      <p className="text-sm text-gray-400">{description}</p>
    </Link>
  )
}

function formatStorage(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}
