import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useSession } from './context/SessionContext.jsx'
import Landing from './screens/Landing.jsx'
import Shell from './components/Shell.jsx'
import Dashboard from './screens/Dashboard.jsx'
import Chat from './screens/Chat.jsx'
import MonthlySummary from './screens/MonthlySummary.jsx'
import Upload from './screens/Upload.jsx'
import Transactions from './screens/Transactions.jsx'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg, #FAF8F5)', padding: 24 }}>
          <div style={{ background: '#fff', borderRadius: 20, padding: '36px 32px', maxWidth: 480, textAlign: 'center', boxShadow: '0 10px 40px rgba(0,0,0,0.08)' }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>⚠</div>
            <h2 style={{ fontFamily: 'Fraunces, Georgia, serif', margin: '0 0 8px', color: '#231E17' }}>Something went wrong</h2>
            <p style={{ color: '#7E7668', fontSize: 14, margin: '0 0 20px', wordBreak: 'break-word' }}>
              {this.state.error?.message || 'An unexpected rendering error occurred.'}
            </p>
            <button
              style={{ background: '#D97B3F', color: '#fff', border: 0, padding: '10px 22px', borderRadius: 10, fontWeight: 600, cursor: 'pointer' }}
              onClick={() => { sessionStorage.clear(); window.location.href = '/' }}
            >
              Restart Session
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function App() {
  const { session } = useSession()

  // ── No session: show the name/landing screen (full-page, outside Shell) ──
  if (!session) {
    return (
      <ErrorBoundary>
        <Landing />
      </ErrorBoundary>
    )
  }

  // ── Active session: show the full shell + all routes ─────────────────────
  // Every session from the landing flow is brand-new, so always start on Upload.
  // The user can navigate freely once they're in.
  return (
    <ErrorBoundary>
      <Routes>
        <Route element={<Shell />}>
          {/* Default entry for a fresh session: upload first */}
          <Route index element={<Navigate to="/upload" replace />} />
          <Route path="/dashboard"    element={<Dashboard />} />
          <Route path="/chat"         element={<Chat />} />
          <Route path="/summary"      element={<MonthlySummary />} />
          <Route path="/upload"       element={<Upload />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="*"             element={<Navigate to="/upload" replace />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  )
}
