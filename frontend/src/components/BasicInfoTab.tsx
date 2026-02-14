import { useState, useEffect } from 'react'
import AvatarUploader from './AvatarUploader'
import { userService } from '../services/userService'
import type { UserProfileDetail, EnhancedUserStats } from '../types/user'

interface BasicInfoTabProps {
  token: string
}

export default function BasicInfoTab({ token }: BasicInfoTabProps) {
  const [profile, setProfile] = useState<UserProfileDetail | null>(null)
  const [stats, setStats] = useState<EnhancedUserStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  // Form state
  const [displayName, setDisplayName] = useState('')
  const [bio, setBio] = useState('')
  const [location, setLocation] = useState('')
  const [website, setWebsite] = useState('')
  const [githubUrl, setGithubUrl] = useState('')

  // Load profile
  useEffect(() => {
    loadProfile()
  }, [token])

  const loadProfile = async () => {
    setLoading(true)
    setError('')

    try {
      const [profileData, statsData] = await Promise.all([
        userService.getUserProfile(token),
        userService.getEnhancedUserStats(token),
      ])
      setProfile(profileData)
      setStats(statsData)
      setDisplayName(profileData.display_name || '')
      setBio(profileData.bio || '')
      setLocation(profileData.location || '')
      setWebsite(profileData.website || '')
      setGithubUrl(profileData.github_url || '')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load profile')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError('')
    setSuccess(false)

    try {
      await userService.updateUserProfile(token, {
        display_name: displayName.trim() || undefined,
        bio: bio.trim() || undefined,
        location: location.trim() || undefined,
        website: website.trim() || undefined,
        github_url: githubUrl.trim() || undefined,
      })
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
      await loadProfile()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile')
    } finally {
      setSaving(false)
    }
  }

  const handleAvatarUpload = async (file: File) => {
    try {
      await userService.uploadAvatar(token, file)
      await loadProfile()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload avatar')
      throw err
    }
  }

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin text-2xl neon-text">◌</div>
        <p className="text-gray-400 mt-2">Loading profile...</p>
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

      {/* Success Message */}
      {success && (
        <div className="p-4 border border-green-500/50 rounded bg-green-500/10 flex justify-between items-center">
          <p className="text-sm text-green-400">Profile updated successfully!</p>
          <button onClick={() => setSuccess(false)} className="text-green-400 hover:text-white">✕</button>
        </div>
      )}

      {/* User Info Cards */}
      {profile && (
        <div className="cyber-card p-4">
          <h3 className="text-sm font-semibold text-cyan-300 tracking-wider mb-3">
            <span className="text-cyan-400 mr-2">📋</span>ACCOUNT INFO
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-gray-500">ID:</span>
              <span className="text-gray-300 font-mono">#{profile.id}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Registered:</span>
              <span className="text-gray-300">{formatDate(stats?.member_since)}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Last Login:</span>
              <span className="text-gray-300">{formatDate(stats?.last_login_at)}</span>
            </div>
          </div>
        </div>
      )}

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Agents Count */}
          <div className="cyber-card p-4 hover:border-cyan-500/50 transition-all">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl
                              bg-gradient-to-br from-cyan-500/20 to-purple-500/20 border border-cyan-500/30">
                🤖
              </div>
              <div>
                <p className="text-2xl font-bold neon-text">{stats.agents_count}</p>
                <p className="text-xs text-gray-500 uppercase tracking-wider">Digital Humans</p>
              </div>
            </div>
          </div>

          {/* Conversations Count */}
          <div className="cyber-card p-4 hover:border-purple-500/50 transition-all">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl
                              bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-purple-500/30">
                💬
              </div>
              <div>
                <p className="text-2xl font-bold text-purple-400">{stats.total_conversations}</p>
                <p className="text-xs text-gray-500 uppercase tracking-wider">Conversations</p>
              </div>
            </div>
          </div>

          {/* Training Tasks Count */}
          <div className="cyber-card p-4 hover:border-pink-500/50 transition-all">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl
                              bg-gradient-to-br from-pink-500/20 to-orange-500/20 border border-pink-500/30">
                🎓
              </div>
              <div>
                <p className="text-2xl font-bold text-pink-400">{stats.total_training_tasks}</p>
                <p className="text-xs text-gray-500 uppercase tracking-wider">Training Tasks</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Avatar Section */}
        <div className="md:col-span-1 flex flex-col items-center">
          <AvatarUploader
            currentAvatar={profile?.avatar_url || null}
            onUpload={handleAvatarUpload}
            size="lg"
          />
          {profile && (
            <div className="mt-4 text-center">
              <p className="text-lg font-semibold text-cyan-400">{profile.username}</p>
              <p className="text-sm text-gray-400">{profile.email}</p>
            </div>
          )}
        </div>

        {/* Form Section */}
        <div className="md:col-span-2 space-y-4">
          <div>
            <label className="block text-sm font-medium text-purple-300 mb-2">
              DISPLAY NAME
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
              placeholder="How should we call you?"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-purple-300 mb-2">
              BIO
            </label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all resize-none"
              placeholder="Tell us a little about yourself..."
              rows={3}
              maxLength={500}
            />
            <p className="text-xs text-gray-500 mt-1">{bio.length}/500</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-purple-300 mb-2">
              LOCATION
            </label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
              placeholder="City, Country"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-purple-300 mb-2">
              WEBSITE
            </label>
            <input
              type="url"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
              placeholder="https://yourwebsite.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-purple-300 mb-2">
              GITHUB
            </label>
            <input
              type="url"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
              placeholder="https://github.com/username"
            />
          </div>

          {/* Save Button */}
          <div className="flex justify-end pt-4">
            <button
              onClick={handleSave}
              disabled={saving}
              className="cyber-btn px-8 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
