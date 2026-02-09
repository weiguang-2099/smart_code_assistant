import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { useEffect, useState } from 'react'
import EditorPage from './pages/EditorPage'
import ProjectsPage from './pages/ProjectsPage'
import CodeGenPage from './pages/CodeGenPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DocumentsPage from './pages/DocumentsPage'
import DocumentEditorPage from './pages/DocumentEditorPage'
import ProfilePage from './pages/ProfilePage'

// Particle component for background effect - optimized
function Particles() {
  const [particles, setParticles] = useState<number[]>([])

  useEffect(() => {
    const count = 15 // Reduced from 20 for better performance
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
            animationDelay: `${Math.random() * 20}s`,
            animationDuration: `${20 + Math.random() * 15}s` // Slower, varied speeds
          }}
        />
      ))}
    </div>
  )
}

function Navbar() {
  const { user, isAuthenticated, logout } = useAuth()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <nav className="backdrop-blur-md bg-opacity-80 shadow-lg border-b border-cyan-500/30 relative z-50"
         style={{ background: 'rgba(10, 10, 15, 0.9)' }}>
      <div className="w-full px-3 sm:px-4 lg:px-6">
        <div className="flex items-center justify-between h-14 sm:h-16">
          {/* Logo */}
          <div className="flex-shrink-0">
            <Link to="/" className="text-lg sm:text-2xl font-bold tracking-wider neon-text float-animation">
              &lt;SC&gt;
            </Link>
          </div>

          {/* Desktop Navigation - Scrollable on medium screens */}
          <div className="hidden lg:flex flex-1 items-center justify-center px-4">
            <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-thin">
              <Link to="/" className="cyber-btn text-xs px-2 py-1.5 whitespace-nowrap">
                Home
              </Link>
              <Link to="/projects" className="cyber-btn text-xs px-2 py-1.5 whitespace-nowrap">
                Projects
              </Link>
              <Link to="/documents" className="cyber-btn text-xs px-2 py-1.5 whitespace-nowrap" style={{ borderColor: 'var(--color-neon-purple)', color: 'var(--color-neon-purple)' }}>
                Docs
              </Link>
              <Link to="/editor" className="cyber-btn text-xs px-2 py-1.5 whitespace-nowrap">
                Editor
              </Link>
              <Link to="/generate" className="cyber-btn text-xs px-2 py-1.5 whitespace-nowrap">
                Generate
              </Link>
              <Link to="/review" className="cyber-btn text-xs px-2 py-1.5 whitespace-nowrap">
                Review
              </Link>
            </div>
          </div>

          {/* User Actions */}
          <div className="hidden lg:flex items-center gap-1.5">
            {isAuthenticated ? (
              <>
                <Link to="/profile" className="cyber-btn text-xs px-2 py-1.5 whitespace-nowrap" style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}>
                  Profile
                </Link>
                <button
                  onClick={logout}
                  className="cyber-btn text-xs px-2 py-1.5 whitespace-nowrap"
                  style={{ borderColor: 'var(--color-neon-pink)', color: 'var(--color-neon-pink)' }}
                >
                  Logout
                </button>
                <span className="text-xs text-cyan-300 px-2 py-1.5 border border-cyan-500/30 rounded whitespace-nowrap max-w-24 truncate">
                  {user?.username}
                </span>
              </>
            ) : (
              <>
                <Link to="/login" className="cyber-btn text-xs px-3 py-1.5">
                  Login
                </Link>
                <Link
                  to="/register"
                  className="cyber-btn text-xs px-3 py-1.5"
                  style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
                >
                  Register
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="lg:hidden flex items-center gap-2">
            {isAuthenticated && (
              <span className="text-xs text-cyan-300 px-2 py-1 border border-cyan-500/30 rounded max-w-20 truncate">
                {user?.username}
              </span>
            )}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="cyber-btn text-xs px-2 py-1.5"
            >
              {mobileMenuOpen ? '✕' : '☰'}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden" style={{ background: 'rgba(10, 10, 15, 0.98)' }}>
          <div className="px-3 pt-2 pb-4 space-y-1">
            <Link
              to="/"
              className="block cyber-btn text-xs px-3 py-2 w-full text-left"
              onClick={() => setMobileMenuOpen(false)}
            >
              Home
            </Link>
            <Link
              to="/projects"
              className="block cyber-btn text-xs px-3 py-2 w-full text-left"
              onClick={() => setMobileMenuOpen(false)}
            >
              Projects
            </Link>
            <Link
              to="/documents"
              className="block cyber-btn text-xs px-3 py-2 w-full text-left"
              style={{ borderColor: 'var(--color-neon-purple)', color: 'var(--color-neon-purple)' }}
              onClick={() => setMobileMenuOpen(false)}
            >
              Documents
            </Link>
            <Link
              to="/editor"
              className="block cyber-btn text-xs px-3 py-2 w-full text-left"
              onClick={() => setMobileMenuOpen(false)}
            >
              Editor
            </Link>
            <Link
              to="/generate"
              className="block cyber-btn text-xs px-3 py-2 w-full text-left"
              onClick={() => setMobileMenuOpen(false)}
            >
              Generate
            </Link>
            <Link
              to="/review"
              className="block cyber-btn text-xs px-3 py-2 w-full text-left"
              onClick={() => setMobileMenuOpen(false)}
            >
              Review
            </Link>
            {isAuthenticated && (
              <>
                <Link
                  to="/profile"
                  className="block cyber-btn text-xs px-3 py-2 w-full text-left"
                  style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Profile
                </Link>
                <button
                  onClick={() => {
                    logout()
                    setMobileMenuOpen(false)
                  }}
                  className="block cyber-btn text-xs px-3 py-2 w-full text-left"
                  style={{ borderColor: 'var(--color-neon-pink)', color: 'var(--color-neon-pink)' }}
                >
                  Logout
                </button>
              </>
            )}
            {!isAuthenticated && (
              <>
                <Link
                  to="/login"
                  className="block cyber-btn text-xs px-3 py-2 w-full text-left"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  className="block cyber-btn text-xs px-3 py-2 w-full text-left"
                  style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Register
                </Link>
              </>
            )}
          </div>
        </div>
      )}
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
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/documents/:id" element={<DocumentEditorPage />} />
            <Route path="/documents/:id/edit" element={<DocumentEditorPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/editor" element={<EditorPage />} />
            <Route path="/generate" element={<CodeGenPage />} />
            <Route path="/review" element={<CodeGenPage />} />
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
