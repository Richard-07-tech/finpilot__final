// ---------------------------------------------------------------------------
// FinPilot — Session Context
//
// Provides a per-tab anonymous session: a random UUID v4 as the real user_id
// and a display name that is NEVER sent to the backend as an identifier.
//
// Storage: sessionStorage
//   ✓ Persists through page refresh (same tab)  — stays "logged in"
//   ✓ Cleared on tab close / new tab            — fresh session each visit
//   ✗ NOT localStorage — that would persist across browser restarts and
//     let a judge reopen the demo and collide with a prior session UUID.
// ---------------------------------------------------------------------------

import React, { createContext, useContext, useCallback, useState } from 'react'

// Storage keys
export const SK_USER_ID   = 'fp_user_id'
export const SK_DISP_NAME = 'fp_display_name'
// Legacy upload gate keys (still used by Upload + Chat screens)
export const UPLOAD_PROCESSING_KEY = 'finpilot_processing_upload'
export const HAS_DATA_KEY          = 'finpilot_has_data'

// -------------------------------------------------------------------
// UUID v4 — uses crypto.randomUUID when available (all modern browsers),
// falls back to a manual implementation for older environments.
// -------------------------------------------------------------------
function uuid4() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  // Fallback: RFC 4122 compliant v4
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

// -------------------------------------------------------------------
// Context shape
// -------------------------------------------------------------------
const SessionCtx = createContext(null)

/**
 * Reads an existing session from sessionStorage.
 * Returns { userId, displayName } or null if none exists.
 */
function readSession() {
  const userId      = sessionStorage.getItem(SK_USER_ID)
  const displayName = sessionStorage.getItem(SK_DISP_NAME)
  if (userId && displayName) return { userId, displayName }
  return null
}

/**
 * Persists a new session to sessionStorage and returns it.
 */
function writeSession(displayName) {
  const userId = uuid4()
  sessionStorage.setItem(SK_USER_ID, userId)
  sessionStorage.setItem(SK_DISP_NAME, displayName)
  return { userId, displayName }
}

/**
 * Clears all session state from sessionStorage (including upload gate keys).
 */
function clearSession() {
  sessionStorage.removeItem(SK_USER_ID)
  sessionStorage.removeItem(SK_DISP_NAME)
  sessionStorage.removeItem('finpilot_session_id') // chat session_id
  sessionStorage.removeItem(UPLOAD_PROCESSING_KEY)
  sessionStorage.removeItem(HAS_DATA_KEY)
  // Defensively clear any legacy localStorage keys
  try {
    localStorage.removeItem(UPLOAD_PROCESSING_KEY)
    localStorage.removeItem(HAS_DATA_KEY)
  } catch { /* ignore */ }
}

// -------------------------------------------------------------------
// Provider
// -------------------------------------------------------------------
export function SessionProvider({ children }) {
  const [session, setSession] = useState(() => readSession())

  /** Called from the landing screen once the user submits their name. */
  const startSession = useCallback((displayName) => {
    const sess = writeSession(displayName.trim())
    setSession(sess)
  }, [])

  /** Called from "Start Over" in the sidebar. */
  const resetSession = useCallback(() => {
    clearSession()
    setSession(null)
  }, [])

  return (
    <SessionCtx.Provider value={{ session, startSession, resetSession }}>
      {children}
    </SessionCtx.Provider>
  )
}

// -------------------------------------------------------------------
// Hook
// -------------------------------------------------------------------
export function useSession() {
  const ctx = useContext(SessionCtx)
  if (!ctx) throw new Error('useSession must be used inside <SessionProvider>')
  return ctx
}
