// ---------------------------------------------------------------------------
// FinPilot — Centralized API service
// Base URL comes from VITE_API_BASE env var so the same code works in dev
// (localhost:8000) and prod without changes.
//
// IMPORTANT: There is no USER_ID constant here. The caller must always pass
// the session UUID from SessionContext as userId. This prevents accidental
// use of a hardcoded test value.
// ---------------------------------------------------------------------------

const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// ---- helpers ---------------------------------------------------------------

async function request(path, opts = {}) {
  const url = `${BASE}${path}`
  const res = await fetch(url, opts)
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    let detail = body
    try { detail = JSON.parse(body).detail || body } catch { /* not JSON */ }
    throw new Error(detail || `${res.status} ${res.statusText}`)
  }
  return res.json()
}

function json(path, body) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

// ---- Chat ------------------------------------------------------------------

export function postChat({ session_id, user_id, message }) {
  return json('/chat', { session_id, user_id, message })
}

// ---- Uploads ---------------------------------------------------------------

export function createUpload(file, userId) {
  const form = new FormData()
  form.append('file', file)
  return request(`/uploads?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
    body: form,
  })
}

export function getUploadStatus(uploadId) {
  return request(`/uploads/${uploadId}`)
}

// ---- Intelligence ----------------------------------------------------------

export function getMonthlySummary(month, currency = 'INR') {
  const params = new URLSearchParams({ month, currency })
  return request(`/intelligence/monthly-summary?${params}`)
}

export function getTransactions(userId, { month, category } = {}) {
  const params = new URLSearchParams()
  if (userId) params.set('user_id', userId)
  if (month) params.set('month', month)
  if (category) params.set('category', category)
  const qs = params.toString()
  return request(`/intelligence/transactions${qs ? `?${qs}` : ''}`)
}

export function postCategoryCorrection({ user_id, merchant, category }) {
  return json('/intelligence/category-correction', { user_id, merchant, category })
}
