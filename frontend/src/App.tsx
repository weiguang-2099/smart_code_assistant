import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { useEffect, useState } from 'react'
import EditorPage from './pages/EditorPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'

// Particle component for background effect
function Particles() {
  const [particles, setParticles] = useState<number[]>([])

  useEffect(() => {
    const count = 50
    setParticles(Array.from({ length: count }, (_, i) => i))
  }, [])

  return (
    <div className="particles">
      {particles.map((i) => (
        <div
          key={i}
          className="particle"
          style={{
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 15}s`,
            animationDuration: `${10 + Math.random() * 10}s`
          }}
        />
      ))}
    </div>
  )
}

function Navbar() {
  const { user, isAuthenticated, logout } = useAuth()

  return (
    <nav className="backdrop-blur-md bg-opacity-80 shadow-lg border-b border-cyan-500/30"
         style={{ background: 'rgba(10, 10, 15, 0.8)' }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="text-2xl font-bold tracking-wider neon-text float-animation">
              &lt;SMART CODE /&gt;
            </Link>
          </div>
          <div className="hidden md:block">
            <div className="ml-10 flex items-center space-x-2">
              <Link to="/" className="cyber-btn text-sm">
                Home
              </Link>
              <Link to="/editor" className="cyber-btn text-sm">
                Editor
              </Link>
              <Link to="/generate" className="cyber-btn text-sm">
                Generate
              </Link>
              <Link to="/review" className="cyber-btn text-sm">
                Review
              </Link>

              {isAuthenticated ? (
                <>
                  <span className="text-sm text-cyan-300 ml-4 px-4 py-2 border border-cyan-500/30 rounded">
                    Welcome, {user?.username}
                  </span>
                  <button
                    onClick={logout}
                    className="cyber-btn text-sm"
                    style={{ borderColor: 'var(--color-neon-pink)', color: 'var(--color-neon-pink)' }}
                  >
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <Link to="/login" className="cyber-btn text-sm">
                    Login
                  </Link>
                  <Link
                    to="/register"
                    className="cyber-btn text-sm"
                    style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
                  >
                    Register
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}

function HomePage() {
  const { isAuthenticated } = useAuth()

  return (
    <div className="text-center py-12 relative z-10">
      <div className="mb-8">
        <h1 className="text-6xl font-bold mb-4 neon-text tracking-widest">
          SMART CODE ASSISTANT
        </h1>
        <div className="h-1 w-64 mx-auto cyber-border"></div>
      </div>

      <p className="text-xl text-cyan-300 mb-12 tracking-wide">
        AI-Powered Code Generation & Review Platform
      </p>

      {!isAuthenticated && (
        <div className="flex justify-center gap-6 mb-16">
          <Link
            to="/register"
            className="cyber-btn text-lg px-8 py-4"
            style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
          >
            &gt; INITIALIZE &lt;
          </Link>
          <Link
            to="/login"
            className="cyber-btn text-lg px-8 py-4"
            style={{ borderColor: 'var(--color-neon-purple)', color: 'var(--color-neon-purple)' }}
          >
            &gt; ACCESS &lt;
          </Link>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto px-4">
        <div className="cyber-card p-8 float-animation" style={{ animationDelay: '0s' }}>
          <div className="text-4xl mb-4">{'</>'}</div>
          <h3 className="text-2xl font-semibold neon-text mb-4 tracking-wider">
            CODE EDITOR
          </h3>
          <p className="text-gray-400 leading-relaxed">
            Advanced code editor powered by Monaco with syntax highlighting and intelligent completion
          </p>
          <div className="mt-6 h-px bg-gradient-to-r from-transparent via-cyan-500 to-transparent"></div>
        </div>

        <div className="cyber-card p-8 float-animation" style={{ animationDelay: '0.5s' }}>
          <div className="text-4xl mb-4">{'<AI>'}</div>
          <h3 className="text-2xl font-semibold neon-text-purple mb-4 tracking-wider">
            AI GENERATION
          </h3>
          <p className="text-gray-400 leading-relaxed">
            Generate intelligent code using advanced LangGraph Agents with multi-step reasoning
          </p>
          <div className="mt-6 h-px bg-gradient-to-r from-transparent via-purple-500 to-transparent"></div>
        </div>

        <div className="cyber-card p-8 float-animation" style={{ animationDelay: '1s' }}>
          <div className="text-4xl mb-4">{'{Review}'}</div>
          <h3 className="text-2xl font-semibold mb-4 tracking-wider" style={{ color: 'var(--color-neon-pink)', textShadow: '0 0 10px var(--color-neon-pink)' }}>
            CODE REVIEW
          </h3>
          <p className="text-gray-400 leading-relaxed">
            Automated code analysis with intelligent suggestions and security vulnerability detection
          </p>
          <div className="mt-6 h-px bg-gradient-to-r from-transparent via-pink-500 to-transparent"></div>
        </div>
      </div>

      <div className="mt-16 cyber-card max-w-2xl mx-auto p-6">
        <div className="flex items-center justify-center gap-4 text-sm text-gray-500">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
            SYSTEM ONLINE
          </span>
          <span>|</span>
          <span>v1.0.0</span>
          <span>|</span>
          <span>SECURE CONNECTION</span>
        </div>
      </div>
    </div>
  )
}

function AppContent() {
  return (
    <div className="min-h-screen relative overflow-hidden">
      <Particles />
      <div className="relative z-10">
        <Navbar />
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/editor" element={<EditorPage />} />
            <Route path="/generate" element={
              <div className="text-center py-20">
                <h2 className="text-4xl font-bold neon-text mb-4">CODE GENERATION</h2>
                <p className="text-cyan-300">Module loading...</p>
              </div>
            } />
            <Route path="/review" element={
              <div className="text-center py-20">
                <h2 className="text-4xl font-bold neon-text-purple mb-4">CODE REVIEW</h2>
                <p className="text-purple-300">Module loading...</p>
              </div>
            } />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  )
}

export default App
