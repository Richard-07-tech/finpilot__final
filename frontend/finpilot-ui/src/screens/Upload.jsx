import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon, DropArt } from '../components/ui.jsx'
import { upload as u } from '../data/mock.js'
import { createUpload, getUploadStatus } from '../api.js'
import { useSession, UPLOAD_PROCESSING_KEY, HAS_DATA_KEY } from '../context/SessionContext.jsx'

// Re-export so Chat.jsx can import from one canonical place
export { UPLOAD_PROCESSING_KEY, HAS_DATA_KEY }

export default function Upload() {
  const navigate = useNavigate()
  const { session } = useSession()
  const userId = session?.userId
  const [phase, setPhase] = useState('idle') // idle | uploading | processing | done | error
  const [uploadId, setUploadId] = useState(null)
  const [uploadResult, setUploadResult] = useState(null)
  const [fileName, setFileName] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef(null)
  const pollRef = useRef(null)
  const redirectTimerRef = useRef(null)

  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current)
    if (redirectTimerRef.current) clearTimeout(redirectTimerRef.current)
  }, [])

  const startUpload = async (file) => {
    if (phase === 'uploading' || phase === 'processing') return

    const activeUserId = userId || sessionStorage.getItem('fp_user_id')
    if (!activeUserId) {
      setErrorMsg('No active session found. Please return to the landing screen.')
      setPhase('error')
      return
    }

    setPhase('uploading')
    setFileName(file.name)
    setErrorMsg('')
    setUploadResult(null)

    try {
      const res = await createUpload(file, activeUserId)
      setUploadId(res.upload_id)
      // Signal to other screens in this session that a background job is running
      sessionStorage.setItem(UPLOAD_PROCESSING_KEY, res.upload_id)
      setPhase('processing')

      // Poll for status immediately and then every 1000ms
      let consecutiveErrors = 0
      const poll = async () => {
        try {
          const status = await getUploadStatus(res.upload_id)
          consecutiveErrors = 0
          if (status.status === 'completed') {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            // Mark data as available for the rest of the app
            sessionStorage.removeItem(UPLOAD_PROCESSING_KEY)
            sessionStorage.setItem(HAS_DATA_KEY, '1')
            setUploadResult(status)
            setPhase('done')
            // Transition to Chat once genuinely completed
            redirectTimerRef.current = setTimeout(() => {
              navigate('/chat')
            }, 1200)
          } else if (status.status === 'failed') {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            sessionStorage.removeItem(UPLOAD_PROCESSING_KEY)
            setErrorMsg(status.error_message || 'Upload processing failed')
            setPhase('error')
          }
        } catch (err) {
          consecutiveErrors++
          if (consecutiveErrors >= 5) {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            sessionStorage.removeItem(UPLOAD_PROCESSING_KEY)
            setErrorMsg(`Status check failed: ${err.message}`)
            setPhase('error')
          }
        }
      }

      // Run immediately, then every 1 second
      poll()
      pollRef.current = setInterval(poll, 1000)
    } catch (err) {
      sessionStorage.removeItem(UPLOAD_PROCESSING_KEY)
      setErrorMsg(err.message || 'Upload failed')
      setPhase('error')
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer?.files?.[0]
    if (file) startUpload(file)
  }

  const handleFileSelect = (e) => {
    const file = e.target?.files?.[0]
    if (file) startUpload(file)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const reset = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    if (redirectTimerRef.current) clearTimeout(redirectTimerRef.current)
    sessionStorage.removeItem(UPLOAD_PROCESSING_KEY)
    setPhase('idle')
    setUploadId(null)
    setUploadResult(null)
    setFileName('')
    setErrorMsg('')
  }

  const flaggedRows = uploadResult?.flagged_rows || []

  return (
    <div>
      <div className="page-head">
        <span className="eyebrow plain">{u.eyebrow}</span>
        <h1>{u.heading}</h1>
        <p className="muted" style={{ maxWidth: 620, margin: 0 }}>{u.description}</p>
      </div>

      <div className="grid2">
        {/* Left: drop zone + states */}
        <div className="stack">
          <div
            className={`dropzone${dragOver ? ' over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => phase === 'idle' && fileInputRef.current?.click()}
            role="button" tabIndex={0}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.pdf,.jpg,.jpeg,.png"
              style={{ display: 'none' }}
              onChange={handleFileSelect}
            />

            {phase === 'idle' && (
              <>
                <DropArt size={88} />
                <div className="dz-title">{u.drop.heading}</div>
                <p className="muted small" style={{ maxWidth: 360, margin: '0 auto 16px' }}>{u.drop.helper}</p>
                <button className="btn btn-primary" onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click() }}>
                  <Icon name="upload" size={15} />{u.drop.button}
                </button>
              </>
            )}

            {phase === 'uploading' && (
              <>
                <div className="spinner" />
                <div className="dz-title">Uploading {fileName}</div>
                <div className="small muted">Sending file to server…</div>
              </>
            )}

            {phase === 'processing' && (
              <>
                <div className="spinner" />
                <div className="dz-title">Processing {fileName}…</div>
                <div className="small muted">Parsing rows, matching merchants, auto-categorizing</div>
              </>
            )}

            {phase === 'done' && (
              <>
                <div className="var-ic" style={{ background: 'var(--green-soft)', color: 'var(--green)', margin: '0 auto' }}>
                  <Icon name="check" size={20} />
                </div>
                <div className="dz-title">Import complete</div>
                <p className="small muted" style={{ margin: '4px 0 0' }}>
                  {fileName} · {uploadResult?.row_count ?? 0} rows parsed
                </p>
                <div className="small muted" style={{ marginTop: 6, color: 'var(--accent-dark)', fontWeight: 500 }}>
                  Connecting to Chat in a moment…
                </div>
                <div className="row" style={{ gap: 10, marginTop: 14, justifyContent: 'center' }}>
                  <button className="btn btn-primary" onClick={(e) => { e.stopPropagation(); navigate('/chat') }}>
                    <Icon name="send" size={15} />Go to Chat
                  </button>
                  <button className="btn btn-outline" onClick={(e) => { e.stopPropagation(); reset() }}>
                    Import another
                  </button>
                </div>
              </>
            )}

            {phase === 'error' && (
              <>
                <div className="var-ic" style={{ background: '#F5E2E0', color: '#B04A3C', margin: '0 auto' }}>
                  <Icon name="alert" size={20} />
                </div>
                <div className="dz-title">Import failed</div>
                <p className="small" style={{ margin: '4px 0 0', color: '#B04A3C' }}>{errorMsg}</p>
                <button className="btn btn-outline" style={{ marginTop: 16 }} onClick={(e) => { e.stopPropagation(); reset() }}>
                  Try again
                </button>
              </>
            )}
          </div>

          {phase === 'done' && flaggedRows.length > 0 && (
            <div className="card">
              <div className="row between" style={{ marginBottom: 6 }}>
                <h3 className="section-title" style={{ fontSize: 16 }}>Rows needing attention</h3>
                <span className="pill amber"><span className="pdot" />{flaggedRows.length} flagged</span>
              </div>
              {flaggedRows.map((f, i) => {
                const tx = f.transaction || {}
                const title = tx.merchant || f.merchant || f.field || 'Flagged Transaction'
                const reason = f.reason || f.message || 'Needs review'
                const extra = tx.amount != null ? `${tx.date ? tx.date + ' · ' : ''}$${Math.abs(Number(tx.amount)).toFixed(2)}` : ''
                return (
                  <div key={i} className="flag-row">
                    <div className="var-ic" style={{ background: 'var(--gray-soft)', color: 'var(--gray)', width: 34, height: 34 }}>
                      <Icon name="flag" size={16} />
                    </div>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div className="row between" style={{ gap: 8 }}>
                        <div style={{ fontWeight: 600 }}>{title}</div>
                        {extra && <div className="small muted" style={{ fontWeight: 500 }}>{extra}</div>}
                      </div>
                      <div className="small muted">{reason}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {phase === 'done' && flaggedRows.length === 0 && (
            <div className="card" style={{ textAlign: 'center', padding: '30px 20px' }}>
              <div className="var-ic" style={{ background: 'var(--green-soft)', color: 'var(--green)', margin: '0 auto 10px' }}>
                <Icon name="check" size={20} />
              </div>
              <div style={{ fontWeight: 600 }}>All rows imported cleanly</div>
              <div className="small muted">No flagged items to review.</div>
            </div>
          )}
        </div>

        {/* Right column */}
        <aside className="stack">
          <div className="card">
            <h3 className="section-title" style={{ fontSize: 16 }}>Supported Institutions</h3>
            <div className="small muted" style={{ margin: '4px 0 12px' }}>Direct import formats verified for:</div>
            <div className="chip-grid">
              {u.institutions.map((b) => (
                <span key={b.name} className="inst-chip"><i style={{ background: b.color }} />{b.name}</span>
              ))}
              <span className="inst-chip" style={{ color: 'var(--accent-dark)', borderStyle: 'dashed' }}>{u.moreInstitutions}</span>
            </div>
          </div>

          <div className="card">
            <h3 className="section-title" style={{ fontSize: 16, marginBottom: 10 }}>{u.formatTitle}</h3>
            <div className="req-box">
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {u.formatRules.map((rule) => <li key={rule}>{rule}</li>)}
              </ul>
            </div>
          </div>

          <div className="card" style={{ background: '#FBF7EF' }}>
            <p className="trust-line" style={{ margin: 0 }}>{u.trustLine}</p>
          </div>
        </aside>
      </div>

      <div className="footer-bar">
        <span className="sync-dot" />
        <span className="small"><b>System status:</b> <span style={{ color: 'var(--green)', fontWeight: 600 }}>{u.footer.status}</span></span>
        <div style={{ marginLeft: 'auto' }} className="row">
          {u.footer.links.map((l) => (
            <a key={l} href={`#${l}`} onClick={(e) => e.preventDefault()} className="small" style={{ fontWeight: 600 }}>{l}</a>
          ))}
        </div>
      </div>
    </div>
  )
}
