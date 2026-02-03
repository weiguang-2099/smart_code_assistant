import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'

interface LoginResponse {
  access_token: string
  token_type: string
  user: {
    id: number
    username: string
    email: string
    full_name?: string
    is_active: boolean
    is_superuser: boolean
  }
}

export default function LoginPage() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const response = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      })

      const data: LoginResponse = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed')
      }

      // Store token and user info
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))

      // Navigate to home or editor
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        <div className="cyber-card p-8">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold neon-text tracking-widest mb-2">
              {'<LOGIN />'}
            </h2>
            <div className="h-px w-48 mx-auto bg-gradient-to-r from-transparent via-cyan-500 to-transparent"></div>
            <p className="mt-4 text-sm text-gray-400">
              Access your neural interface
            </p>
            <p className="mt-2 text-sm">
              Or{' '}
              <Link to="/register" className="font-medium neon-text-purple hover:underline">
                initialize new identity
              </Link>
            </p>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-cyan-300 mb-2">
                  USERNAME / EMAIL
                </label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  className="w-full px-4 py-3 bg-gray-900/50 border border-cyan-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
                  placeholder="Enter your credentials"
                  value={formData.username}
                  onChange={handleChange}
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-cyan-300 mb-2">
                  PASSWORD
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  className="w-full px-4 py-3 bg-gray-900/50 border border-cyan-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
                  placeholder="Enter access code"
                  value={formData.password}
                  onChange={handleChange}
                />
              </div>
            </div>

            {error && (
              <div className="p-4 border border-red-500/50 rounded bg-red-500/10">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="cyber-btn w-full py-3 text-base font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ borderColor: 'var(--color-neon-blue)', color: 'var(--color-neon-blue)' }}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin">◌</span>
                  AUTHENTICATING...
                </span>
              ) : (
                '► INITIALIZE SESSION'
              )}
            </button>

            <div className="text-center pt-4 border-t border-gray-700">
              <Link to="/" className="text-sm text-gray-400 hover:text-cyan-300 transition-colors">
                ← Return to base
              </Link>
            </div>
          </form>
        </div>

        <div className="mt-6 flex items-center justify-center gap-4 text-xs text-gray-600">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            SECURE CONNECTION
          </span>
          <span>|</span>
          <span>ENCRYPTED</span>
        </div>
      </div>
    </div>
  )
}
