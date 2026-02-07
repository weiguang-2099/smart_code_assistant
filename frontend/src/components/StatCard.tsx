import { Link } from 'react-router-dom'

interface StatCardProps {
  icon: string
  label: string
  value: number | string
  unit?: string
  link?: string
  color?: 'cyan' | 'purple' | 'green' | 'pink' | 'yellow'
}

export default function StatCard({
  icon,
  label,
  value,
  unit,
  link,
  color = 'cyan'
}: StatCardProps) {
  const colorStyles = {
    cyan: 'border-cyan-500/30 text-cyan-400',
    purple: 'border-purple-500/30 text-purple-400',
    green: 'border-green-500/30 text-green-400',
    pink: 'border-pink-500/30 text-pink-400',
    yellow: 'border-yellow-500/30 text-yellow-400',
  }

  const gradientStyles = {
    cyan: 'from-cyan-500/20 to-transparent',
    purple: 'from-purple-500/20 to-transparent',
    green: 'from-green-500/20 to-transparent',
    pink: 'from-pink-500/20 to-transparent',
    yellow: 'from-yellow-500/20 to-transparent',
  }

  const content = (
    <>
      <div className="text-4xl mb-2">{icon}</div>
      <div className={`text-3xl font-bold mb-1 ${colorStyles[color].split(' ')[1]}`}>
        {typeof value === 'number' ? value.toLocaleString() : value}
        {unit && <span className="text-lg text-gray-400 ml-1">{unit}</span>}
      </div>
      <div className="text-sm text-gray-400">{label}</div>
    </>
  )

  return (
    <div className="cyber-card p-6 relative overflow-hidden">
      <div className={`absolute inset-0 bg-gradient-to-br ${gradientStyles[color]} opacity-30`} />
      <div className="relative z-10">
        {link ? (
          <Link to={link} className="block hover:scale-105 transition-transform">
            {content}
          </Link>
        ) : (
          content
        )}
      </div>
    </div>
  )
}

interface StatGridProps {
  stats: {
    documents_count?: number
    total_versions?: number
    projects_count?: number
    storage_used?: number
  }
}

export function StatGrid({ stats }: StatGridProps) {
  const formatStorage = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard
        icon="📄"
        label="Documents"
        value={stats.documents_count || 0}
        link="/documents"
        color="cyan"
      />
      <StatCard
        icon="📝"
        label="Total Versions"
        value={stats.total_versions || 0}
        color="purple"
      />
      <StatCard
        icon="📁"
        label="Projects"
        value={stats.projects_count || 0}
        link="/projects"
        color="green"
      />
      <StatCard
        icon="💾"
        label="Storage Used"
        value={formatStorage(stats.storage_used || 0)}
        color="yellow"
      />
    </div>
  )
}
