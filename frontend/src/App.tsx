import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import EditorPage from './pages/EditorPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'

function Navbar() {
  const { user, isAuthenticated, logout } = useAuth()

  return (
    <nav className="bg-primary-600 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="text-xl font-bold hover:text-primary-200">
              Smart Code Assistant
            </Link>
          </div>
          <div className="hidden md:block">
            <div className="ml-10 flex items-center space-x-4">
              <Link to="/" className="hover:bg-primary-700 px-3 py-2 rounded-md text-sm font-medium">
                Home
              </Link>
              <Link to="/editor" className="hover:bg-primary-700 px-3 py-2 rounded-md text-sm font-medium">
                Editor
              </Link>
              <Link to="/generate" className="hover:bg-primary-700 px-3 py-2 rounded-md text-sm font-medium">
                Code Generation
              </Link>
              <Link to="/review" className="hover:bg-primary-700 px-3 py-2 rounded-md text-sm font-medium">
                Code Review
              </Link>

              {isAuthenticated ? (
                <>
                  <span className="text-sm text-primary-200">
                    Welcome, {user?.username}
                  </span>
                  <button
                    onClick={logout}
                    className="bg-primary-700 hover:bg-primary-800 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <Link to="/login" className="hover:bg-primary-700 px-3 py-2 rounded-md text-sm font-medium">
                    Login
                  </Link>
                  <Link
                    to="/register"
                    className="bg-primary-700 hover:bg-primary-800 px-3 py-2 rounded-md text-sm font-medium"
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
    <div className="text-center py-12">
      <h2 className="text-3xl font-bold text-gray-900 mb-4">
        Welcome to Smart Code Assistant
      </h2>
      <p className="text-lg text-gray-600 mb-8">
        AI-powered code generation and review platform
      </p>
      {!isAuthenticated && (
        <div className="space-x-4 mb-8">
          <Link
            to="/register"
            className="bg-primary-600 text-white px-6 py-2 rounded-md hover:bg-primary-700 inline-block"
          >
            Get Started
          </Link>
          <Link
            to="/login"
            className="border border-primary-600 text-primary-600 px-6 py-2 rounded-md hover:bg-primary-50 inline-block"
          >
            Sign In
          </Link>
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Code Editor
          </h3>
          <p className="text-gray-600">
            Advanced code editor with Monaco Editor
          </p>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            AI Generation
          </h3>
          <p className="text-gray-600">
            Generate code with LangGraph Agents
          </p>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Code Review
          </h3>
          <p className="text-gray-600">
            Automated code review and suggestions
          </p>
        </div>
      </div>
    </div>
  )
}

function AppContent() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/editor" element={<EditorPage />} />
          <Route path="/generate" element={<div className="text-2xl">Code Generation Coming Soon</div>} />
          <Route path="/review" element={<div className="text-2xl">Code Review Coming Soon</div>} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Routes>
      </main>
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
