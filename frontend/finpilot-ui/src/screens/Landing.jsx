import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSession } from '../context/SessionContext.jsx'

// FinPilot brand mark (same SVG used in Shell)
function BrandMark() {
  return (
    <svg width="42" height="42" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 20 V12 a8 8 0 0 1 16 0 V20 Z" fill="#F7F4EE" />
      <path d="M9.5 20 v-4.5 a2.5 2.5 0 0 1 5 0 V20 Z" fill="#BC6027" />
    </svg>
  )
}

export default function Landing() {
  const navigate = useNavigate()
  const { startSession } = useSession()
  const [name, setName]   = useState('')
  const [touched, setTouched] = useState(false)

  const invalid = touched && name.trim().length === 0
  const canSubmit = name.trim().length > 0

  const submit = (e) => {
    e.preventDefault()
    setTouched(true)
    if (!canSubmit) return
    startSession(name)
    navigate('/upload')
  }

  return (
    <div className="landing-root" role="main">
      {/* Background decoration */}
      <div className="landing-blob landing-blob-1" aria-hidden="true" />
      <div className="landing-blob landing-blob-2" aria-hidden="true" />

      <div className="landing-card">
        {/* Brand */}
        <div className="landing-brand">
          <div className="landing-mark"><BrandMark /></div>
          <div>
            <div className="landing-product-name">Vantage</div>
            <div className="landing-product-sub">Personal Finance Intelligence</div>
          </div>
        </div>

        {/* Headline */}
        <h1 className="landing-h1">
          Welcome to<br />
          <span className="landing-accent">your finances</span>
        </h1>
        <p className="landing-lead">
          Upload a bank statement and get instant AI-powered insights — spending
          breakdowns, category analysis, savings trends, and more.
        </p>

        {/* Name form */}
        <form onSubmit={submit} className="landing-form" noValidate>
          <label htmlFor="display-name" className="landing-label">
            What should we call you?
          </label>
          <div className={`landing-input-wrap${invalid ? ' invalid' : ''}`}>
            <input
              id="display-name"
              className="landing-input"
              type="text"
              placeholder="e.g. Alex, Maya, Judge #3 …"
              value={name}
              autoFocus
              autoComplete="off"
              onChange={(e) => { setName(e.target.value); setTouched(true) }}
              onKeyDown={(e) => e.key === 'Enter' && submit(e)}
              aria-describedby={invalid ? 'name-error' : undefined}
            />
          </div>
          {invalid && (
            <div id="name-error" className="landing-error" role="alert">
              Please enter a name to continue.
            </div>
          )}

          <button
            type="submit"
            className="landing-cta"
            disabled={!canSubmit}
            id="landing-start-btn"
          >
            Get Started
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </form>

        {/* Trust note */}
        <p className="landing-trust">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          Session-only · no account required · data clears when you close this tab
        </p>

        {/* Feature pills */}
        <div className="landing-pills">
          {['AI-powered chat', 'Category analysis', 'Monthly summaries', 'PDF & CSV support'].map((f) => (
            <span key={f} className="landing-pill">{f}</span>
          ))}
        </div>
      </div>
    </div>
  )
}
