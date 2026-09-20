import React, { useEffect, useRef, useState } from 'react'
import { Icon, ShieldArt, EmptyArt } from '../components/ui.jsx'
import { chat, user } from '../data/mock.js'
import { postChat, getUploadStatus } from '../api.js'
import { useSession, UPLOAD_PROCESSING_KEY, HAS_DATA_KEY } from '../context/SessionContext.jsx'
const SESSION_KEY = 'finpilot_session_id'

export default function Chat() {
  const { session } = useSession()
  const userId = session?.userId
  const displayName = session?.displayName ?? 'you'
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sessionId, setSessionId] = useState(() => sessionStorage.getItem(SESSION_KEY))
  // Upload gate: true while a background upload job hasn't finished yet
  const [uploadGate, setUploadGate] = useState(() => !!sessionStorage.getItem(UPLOAD_PROCESSING_KEY))
  const threadRef = useRef(null)
  const gateTimerRef = useRef(null)

  // Poll upload status immediately and every 1 s until gate clears
  useEffect(() => {
    if (!uploadGate) return
    const checkGate = async () => {
      const uploadId = sessionStorage.getItem(UPLOAD_PROCESSING_KEY)
      if (!uploadId) { setUploadGate(false); return }
      try {
        const status = await getUploadStatus(uploadId)
        if (status.status === 'completed' || status.status === 'failed') {
          sessionStorage.removeItem(UPLOAD_PROCESSING_KEY)
          if (status.status === 'completed') sessionStorage.setItem(HAS_DATA_KEY, '1')
          setUploadGate(false)
        }
      } catch {
        // If we can't reach the status endpoint, don't block forever
        sessionStorage.removeItem(UPLOAD_PROCESSING_KEY)
        setUploadGate(false)
      }
    }
    checkGate()
    gateTimerRef.current = setInterval(checkGate, 1000)
    return () => clearInterval(gateTimerRef.current)
  }, [uploadGate])

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight })
  }, [messages])

  const now = () => new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })

  const send = async (text) => {
    const t = (text ?? draft).trim()
    if (!t || loading) return
    setDraft('')
    setError(null)

    const userMsg = { from: 'user', type: 'text', time: now(), text: t }
    setMessages((ms) => [...ms, userMsg])
    setLoading(true)

    try {
      const res = await postChat({
        session_id: sessionId || undefined,
        user_id: userId,
        message: t,
      })

      // Persist session
      if (res.session_id) {
        setSessionId(res.session_id)
        sessionStorage.setItem(SESSION_KEY, res.session_id)
      }

      const botMsg = { from: 'bot', type: 'text', time: now(), text: res.answer }
      setMessages((ms) => [...ms, botMsg])
    } catch (err) {
      setError(err.message || 'Failed to get response')
      const errMsg = {
        from: 'bot',
        type: 'text',
        time: now(),
        text: `⚠ Sorry, something went wrong: ${err.message || 'Network error'}`,
        isError: true,
      }
      setMessages((ms) => [...ms, errMsg])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-layout">
      {/* Upload gate banner */}
      {uploadGate && (
        <div style={{
          background: 'linear-gradient(90deg,#BC6027 0%,#E07A3A 100%)',
          color: '#fff', padding: '10px 18px', borderRadius: 10, marginBottom: 12,
          display: 'flex', alignItems: 'center', gap: 10, fontSize: 14,
        }}>
          <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2, borderTopColor: '#fff', borderColor: 'rgba(255,255,255,.3)' }} />
          <span><b>Processing your upload…</b> The AI will be ready once categorization is complete.</span>
        </div>
      )}
      {/* Left mini panel */}
      <aside className="chat-side">
        <button className="btn btn-primary" style={{ justifyContent: 'center' }}
          onClick={() => {
            setMessages([])
            setSessionId(null)
            sessionStorage.removeItem(SESSION_KEY)
          }}>
          <Icon name="plus" size={16} />New Analysis
        </button>
        <div className="card recent-box" style={{ padding: 14 }}>
          <div className="eyebrow plain" style={{ marginBottom: 8 }}>Session</div>
          {sessionId ? (
            <div className="recent-item">
              <b>Active session</b>
              <span className="small">{messages.length} messages</span>
            </div>
          ) : (
            <div className="empty-state" style={{ paddingTop: 30 }}>
              <EmptyArt size={56} />
              <div className="small muted">Start a conversation to begin.</div>
            </div>
          )}
        </div>
      </aside>

      {/* Thread */}
      <section className="card chat-main">
        <div className="thread" ref={threadRef}>
          {messages.length === 0 && !loading && (
            <div className="empty-state" style={{ padding: '60px 20px', textAlign: 'center' }}>
              <EmptyArt size={72} />
              <h4 style={{ marginTop: 16 }}>Hi {displayName}! Ask me anything about your finances</h4>
              <p className="muted small" style={{ maxWidth: 360, margin: '0 auto' }}>
                I can analyze your spending, compare months, check budgets, and more.
                Try one of the suggested prompts below.
              </p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.from}`}>
              {m.from === 'bot' && <div className="msg-avatar">{user.botInitials}</div>}
              <div style={{ minWidth: 0 }}>
                <div className={`bubble${m.isError ? ' error-bubble' : ''}`}>
                  {m.text && <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>}
                </div>
                <div className="stamp">{m.time}</div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="msg bot">
              <div className="msg-avatar">{user.botInitials}</div>
              <div style={{ minWidth: 0 }}>
                <div className="bubble">
                  <div className="typing-indicator">
                    <span /><span /><span />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="chips">
          {chat.suggestedPrompts.map((p) => (
            <button key={p} className="chip" onClick={() => send(p)}>{p}</button>
          ))}
        </div>
        <div className="composer">
          <input value={draft} onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            placeholder={uploadGate ? 'Waiting for upload to finish…' : chat.inputPlaceholder}
            disabled={loading || uploadGate} />
          <button className="send-btn" aria-label="Send" onClick={() => send()} disabled={loading || uploadGate}>
            <Icon name="send" size={19} />
          </button>
        </div>
      </section>
    </div>
  )
}
