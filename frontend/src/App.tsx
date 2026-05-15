/**
 * App - Main application with route-level code splitting
 *
 * Performance optimizations:
 * - Lazy loading for all route components
 * - Suspense with loading fallback
 * - Route-based chunk splitting
 */
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ToastProvider } from './contexts/ToastContext'
import ErrorBoundary from './components/ErrorBoundary'
import { LoadingPage } from './components/common/Loading'
import { Suspense, lazy, useEffect, useState, useCallback, useMemo } from 'react'

// Lazy-loaded pages for code splitting
const EditorPage = lazy(() => import('./pages/EditorPage'))
const ProjectsPage = lazy(() => import('./pages/ProjectsPage'))
const CodeGenPage = lazy(() => import('./pages/CodeGenPage'))
const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const DocumentsPage = lazy(() => import('./pages/DocumentsPage'))
const DocumentEditorPage = lazy(() => import('./pages/DocumentEditorPage'))
const ProfilePage = lazy(() => import('./pages/ProfilePage'))
const AgentsPage = lazy(() => import('./pages/AgentsPage'))
const AgentChatPage = lazy(() => import('./pages/AgentChatPage'))
const CodeAnalysisPage = lazy(() => import('./pages/CodeAnalysisPage'))

// Preload critical routes on hover
const preloadPage = (page: string) => {
  switch (page) {
    case 'projects':
      import('./pages/ProjectsPage')
      break
    case 'documents':
      import('./pages/DocumentsPage')
      break
    case 'agents':
      import('./pages/AgentsPage')
      break
    case 'editor':
      import('./pages/EditorPage')
      break
    case 'generate':
      import('./pages/CodeGenPage')
      break
  }
}

// Optimized Particles component with memoization
const Particles = React.memo(function Particles() {
  const [particles, setParticles] = useState<number[]>([])

  useEffect(() => {
    const count = 12
    setParticles(Array.from({ length: count }, (_, i) => i))
  }, [])

  return (
    <div className="particles" aria-hidden="true">
      {particles.map((i) => (
        <div
          key={i}
          className="particle"
          style={{
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 20}s`,
            animationDuration: `${20 + Math.random() * 15}s`,
          }}
        />
      ))}
    </div>
  )
})

// Optimized Navbar with memoization and hover preloading
const Navbar = React.memo(function Navbar() {
  const { user, isAuthenticated, logout } = useAuth()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    setMobileMenuOpen(false)
  }, [location.pathname])

  const handleMouseEnter = useCallback((page: string) => {
    preloadPage(page)
  }, [])

  const navLinks = useMemo(
    () => [
      { to: '/projects', label: 'Projects', preload: 'projects' },
      { to: '/documents', label: 'Docs', preload: 'documents', color: 'purple' },
      { to: '/agents', label: 'Agents', preload: 'agents', color: 'pink' },
      { to: '/editor', label: 'Editor', preload: 'editor' },
      { to: '/generate', label: 'Generate', preload: 'generate' },
      { to: '/code-analysis', label: 'Analysis', preload: 'code-analysis', color: 'green' },
    ],
    []
  )

  const getLinkStyle = useCallback((color?: string) => {
    if (!color) return {}
    const colors: Record<string, string> = {
      purple: 'var(--color-neon-purple)',
      pink: 'var(--color-neon-pink)',
      green: 'var(--color-neon-green)',
    }
    return {
      borderColor: colors[color],
      color: colors[color],
    }
  }, [])

  return (
    <nav
      className="backdrop-blur-md bg-opacity-80 shadow-lg border-b border-cyan-500/30 relative z-50"
      style={{ background: 'rgba(10, 10, 15, 0.9)' }}
    >
      <div className="w-full px-3 sm:px-4 lg:px-6">
        <div className="flex items-center justify-between h-14 sm:h-16">
          <div className="flex-shrink-0">
            <Link to="/" className="text-lg sm:text-2xl font-bold tracking-wider neon-text float-animation">
              &lt;SC&gt;
            </Link>
          </div>

          <div className="hidden lg:flex flex-1 items-center justify-center px-4">
            <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-thin">
              <Link to="/" className="cyber-btn text-xs px-2 py-1.5 whitespace-nowrap">
                Home
              </Link>
              {navLinks.map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  className="cyber-btn text-xs px-2 py-1.5 whitespace-nowrap"
                  style={getLinkStyle(link.color)}
                  onMouseEnter={() => handleMouseEnter(link.preload)}
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </div>

          <div className="hidden lg:flex items-center gap-1.5">
            {isAuthenticated ? (
              <>
                <Link
                  to="/profile"
                  className="cyber-btn text-xs px-2 py-1.5 whitespace-nowrap"
                  style={getLinkStyle('green')}
                >
                  Profile
                </Link>
                <button
                  onClick={logout}
                  className="cyber-btn text-xs px-2 py-1.5 whitespace-nowrap"
                  style={getLinkStyle('pink')}
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
                  style={getLinkStyle('green')}
                >
                  Register
                </Link>
              </>
            )}
          </div>

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

      {mobileMenuOpen && (
        <div className="lg:hidden" style={{ background: 'rgba(10, 10, 15, 0.98)' }}>
          <div className="px-3 pt-2 pb-4 space-y-1">
            <Link to="/" className="block cyber-btn text-xs px-3 py-2 w-full text-left">
              Home
            </Link>
            {navLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="block cyber-btn text-xs px-3 py-2 w-full text-left"
                style={getLinkStyle(link.color)}
              >
                {link.label}
              </Link>
            ))}
            {isAuthenticated ? (
              <>
                <Link
                  to="/profile"
                  className="block cyber-btn text-xs px-3 py-2 w-full text-left"
                  style={getLinkStyle('green')}
                >
                  Profile
                </Link>
                <button
                  onClick={() => logout()}
                  className="block cyber-btn text-xs px-3 py-2 w-full text-left"
                  style={getLinkStyle('pink')}
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="block cyber-btn text-xs px-3 py-2 w-full text-left">
                  Login
                </Link>
                <Link
                  to="/register"
                  className="block cyber-btn text-xs px-3 py-2 w-full text-left"
                  style={getLinkStyle('green')}
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
})

// Home page component
const HomePage = React.memo(function HomePage() {
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
          <h3 className="text-2xl font-semibold neon-text mb-4 tracking-wider">CODE EDITOR</h3>
          <p className="text-gray-400 leading-relaxed">
            Advanced code editor powered by Monaco with syntax highlighting and intelligent completion
          </p>
          <div className="mt-6 h-px bg-gradient-to-r from-transparent via-cyan-500 to-transparent"></div>
        </div>

        <div className="cyber-card p-8 float-animation" style={{ animationDelay: '0.5s' }}>
          <div className="text-4xl mb-4">{'<AI>'}</div>
          <h3 className="text-2xl font-semibold neon-text-purple mb-4 tracking-wider">AI GENERATION</h3>
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
})

// App content with routes
function AppContent() {
  return (
    <div className="min-h-screen relative overflow-hidden">
      <Particles />
      <div className="relative z-10">
        <Navbar />
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Suspense fallback={<LoadingPage message="Loading page..." />}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/documents" element={<DocumentsPage />} />
              <Route path="/documents/:id" element={<DocumentEditorPage />} />
              <Route path="/documents/:id/edit" element={<DocumentEditorPage />} />
              <Route path="/agents" element={<AgentsPage />} />
              <Route path="/agents/:id/chat" element={<AgentChatPage />} />
              <Route path="/code-analysis" element={<CodeAnalysisPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/editor" element={<EditorPage />} />
              <Route path="/generate" element={<CodeGenPage />} />
              <Route path="/review" element={<CodeGenPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <AuthProvider>
          <ToastProvider>
            <AppContent />
          </ToastProvider>
        </AuthProvider>
      </Router>
    </ErrorBoundary>
  )
}

export default App
