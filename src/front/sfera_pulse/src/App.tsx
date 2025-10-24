import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { authService, type LoginRequest } from './api/auth'
import Pulse from './Pulse.tsx'
import WIP from './WIP.tsx'
import './App.css'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [loginForm, setLoginForm] = useState<LoginRequest>({
    username: '',
    password: ''
  })
  const [error, setError] = useState<string>('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await authService.login(loginForm)
      console.log('Login successful:', response)
      setIsLoggedIn(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    await authService.logout()
    setIsLoggedIn(false)
    setLoginForm({ username: '', password: '' })
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setLoginForm(prev => ({
      ...prev,
      [name]: value
    }))
  }

  if (!isLoggedIn) {
    return (
      <div className="app">
        <div className="login-container">
          <h1>Sfera Pulse Login</h1>
          <form onSubmit={handleLogin} className="login-form">
            <div className="form-group">
              <label htmlFor="username">Username:</label>
              <input
                type="text"
                id="username"
                name="username"
                value={loginForm.username}
                onChange={handleInputChange}
                required
                placeholder="Enter your username"
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password:</label>
              <input
                type="password"
                id="password"
                name="password"
                value={loginForm.password}
                onChange={handleInputChange}
                required
                placeholder="Enter your password"
              />
            </div>

            {error && (
              <div className="error-message">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="login-btn"
            >
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <Router>
      <div className="app">
        <Routes>
          <Route path="/pulse" element={<Pulse onLogout={handleLogout} />} />
          <Route path="/wip" element={<WIP onLogout={handleLogout} />} />
          <Route path="/" element={<Navigate to="/pulse" replace />} />
          <Route path="*" element={<Navigate to="/pulse" replace />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
