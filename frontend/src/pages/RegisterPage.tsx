import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'

interface RegisterResponse {
  id: number
  username: string
  email: string
  full_name?: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at: string
  access_token: string
  refresh_token?: string
  token_type: string
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const toast = useToast()
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
    confirmPassword: '',
  })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
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
    setSuccess(false)

    // Validate passwords match
    if (formData.password !== formData.confirmPassword) {
      const errorMsg = 'Passwords do not match'
      setError(errorMsg)
      toast.error(errorMsg)
      return
    }

    // Validate password length
    if (formData.password.length < 6) {
      const errorMsg = 'Password must be at least 6 characters'
      setError(errorMsg)
      toast.error(errorMsg)
      return
    }

    setLoading(true)

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const { confirmPassword, ...registerData } = formData

      const response = await fetch(`${API_URL}/api/v1/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(registerData),
      })

      const data = await response.json()

      if (!response.ok) {
        // Handle new error format
        const errorMessage = data.error?.message || data.detail || 'Registration failed'
        throw new Error(errorMessage)
      }

      const registerData_: RegisterResponse = data

      // Store token and user info using AuthContext
      const userData = {
        id: registerData_.id,
        username: registerData_.username,
        email: registerData_.email,
        full_name: registerData_.full_name,
        is_active: registerData_.is_active,
        is_superuser: registerData_.is_superuser,
      }

      // Use refresh_token if available, otherwise empty string
      login(registerData_.access_token, registerData_.refresh_token || '', userData)

      // Show success message
      setSuccess(true)
      toast.success(`Welcome, ${registerData_.username}! Your identity has been initialized.`)

      // Navigate to home after delay
      setTimeout(() => {
        navigate('/')
      }, 2000)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred'
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        <div className="cyber-card p-8">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold neon-text-purple tracking-widest mb-2">
              {'<REGISTER />'}
            </h2>
            <div className="h-px w-48 mx-auto bg-gradient-to-r from-transparent via-purple-500 to-transparent"></div>
            <p className="mt-4 text-sm text-gray-400">
              Initialize your digital identity
            </p>
            <p className="mt-2 text-sm">
              Or{' '}
              <Link to="/login" className="font-medium neon-text hover:underline">
                access existing account
              </Link>
            </p>
          </div>

          {/* Success Message */}
          {success && (
            <div className="mb-6 p-4 border border-green-500/50 rounded bg-green-500/10 animate-pulse">
              <p className="text-sm text-green-400 text-center">
                ✓ Registration successful! Welcome, {formData.username}!
              </p>
              <p className="text-xs text-green-300 text-center mt-2">
                Redirecting to home...
              </p>
            </div>
          )}

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-purple-300 mb-2">
                  USERNAME *
                </label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  minLength={3}
                  className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
                  placeholder="Choose identifier (min 3 chars)"
                  value={formData.username}
                  onChange={handleChange}
                  disabled={loading || success}
                />
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-purple-300 mb-2">
                  EMAIL ADDRESS *
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
                  placeholder="Enter communication channel"
                  value={formData.email}
                  onChange={handleChange}
                  disabled={loading || success}
                />
              </div>

              <div>
                <label htmlFor="full_name" className="block text-sm font-medium text-purple-300 mb-2">
                  FULL NAME
                </label>
                <input
                  id="full_name"
                  name="full_name"
                  type="text"
                  className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
                  placeholder="Display name (optional)"
                  value={formData.full_name}
                  onChange={handleChange}
                  disabled={loading || success}
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-purple-300 mb-2">
                  PASSWORD *
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  minLength={6}
                  className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
                  placeholder="Create access code (min 6 chars)"
                  value={formData.password}
                  onChange={handleChange}
                  disabled={loading || success}
                />
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-purple-300 mb-2">
                  CONFIRM PASSWORD *
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  required
                  className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
                  placeholder="Verify access code"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  disabled={loading || success}
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
              disabled={loading || success}
              className="cyber-btn w-full py-3 text-base font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin">◌</span>
                  PROCESSING...
                </span>
              ) : success ? (
                <span className="flex items-center justify-center gap-2">
                  <span>✓</span>
                  SUCCESS!
                </span>
              ) : (
                '► CREATE IDENTITY'
              )}
            </button>

            <div className="text-center pt-4 border-t border-gray-700">
              <Link to="/" className="text-sm text-gray-400 hover:text-purple-300 transition-colors">
                ← Return to base
              </Link>
            </div>
          </form>
        </div>

        <div className="mt-6 flex items-center justify-center gap-4 text-xs text-gray-600">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            SECURE REGISTRATION
          </span>
          <span>|</span>
          <span>ENCRYPTED</span>
        </div>
      </div>
    </div>
  )
}
