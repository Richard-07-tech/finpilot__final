import React, { useEffect, useMemo, useState } from 'react'
import { Icon, Pill, fmtMoney } from '../components/ui.jsx'
import { categories } from '../data/mock.js'
import { getTransactions, postCategoryCorrection } from '../api.js'
import { useSession } from '../context/SessionContext.jsx'

// Deterministic color for merchant icon
const PALETTE = [
  { color: '#F6E4D2', ink: '#BC6027' },
  { color: '#E9E8D8', ink: '#6F7046' },
  { color: '#E4F0E8', ink: '#2C7A52' },
  { color: '#EFEDE4', ink: '#5E5647' },
  { color: '#F5E2E0', ink: '#B04A3C' },
  { color: '#F7ECD4', ink: '#96691C' },
  { color: '#E0E8F0', ink: '#3E5C76' },
]
function merchantStyle(name) {
  const safeName = String(name || 'Unknown')
  let h = 0
  for (let i = 0; i < safeName.length; i++) h = ((h << 5) - h + safeName.charCodeAt(i)) | 0
  const p = PALETTE[Math.abs(h) % PALETTE.length]
  return { ...p, initial: safeName.charAt(0).toUpperCase() || '?' }
}

function statusFromTx(tx) {
  if (!tx.category || tx.category === 'Uncategorized') return 'Uncategorized'
  return 'Completed'
}

function CategoryChip({ row, open, onToggle, onSelect }) {
  return (
    <span style={{ position: 'relative', display: 'inline-block' }}>
      <button className="cat-chip" onClick={(e) => { e.stopPropagation(); onToggle(row.id) }}>
        {row.category || 'Uncategorized'}<Icon name="chevronDown" size={13} />
      </button>
      {open && (
        <div className="cat-menu" onClick={(e) => e.stopPropagation()}>
          {categories.map((c) => (
            <button key={c} onClick={() => onSelect(row.id, c)}>
              {c === row.category && <Icon name="check" size={13} />}
              <span style={{ marginLeft: c === row.category ? 0 : 21 }}>{c}</span>
            </button>
          ))}
        </div>
      )}
    </span>
  )
}

export default function Transactions() {
  const { session } = useSession()
  const userId = session?.userId
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [openPicker, setOpenPicker] = useState(null)
  const [q, setQ] = useState('')
  const [correcting, setCorrecting] = useState(null) // id of row being corrected

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    getTransactions(userId)
      .then((data) => {
        if (cancelled) return
        setRows(data.map((tx) => ({
          ...tx,
          ...merchantStyle(tx.merchant),
          status: statusFromTx(tx),
        })))
      })
      .catch((err) => { if (!cancelled) setError(err.message) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [userId])

  const filtered = useMemo(
    () => rows.filter((r) =>
      !q || `${r.merchant} ${r.category || ''} ${r.source_account || ''}`.toLowerCase().includes(q.toLowerCase())),
    [rows, q],
  )

  const changeCategory = async (id, cat) => {
    const row = rows.find((r) => r.id === id)
    if (!row) return
    const prevCategory = row.category
    // Optimistic update
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, category: cat, status: 'Completed' } : r)))
    setOpenPicker(null)
    setCorrecting(id)
    try {
      await postCategoryCorrection({
        user_id: userId,
        merchant: row.merchant,
        category: cat,
      })
    } catch (err) {
      // Revert on failure
      setRows((rs) => rs.map((r) => (r.id === id ? { ...r, category: prevCategory, status: statusFromTx({ ...r, category: prevCategory }) } : r)))
      setError(`Category correction failed: ${err.message}`)
    } finally {
      setCorrecting(null)
    }
  }

  const fmtAmount = (r) => {
    const val = Math.abs(r.amount)
    const sign = r.direction === 'credit' ? '+' : '-'
    return `${sign}${r.currency === 'INR' ? '₹' : '$'}${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  return (
    <div onClick={() => setOpenPicker(null)}>
      <div className="row between page-head" style={{ alignItems: 'flex-start', flexWrap: 'wrap', gap: 14 }}>
        <div>
          <span className="eyebrow plain">Ledger</span>
          <h1 style={{ marginBottom: 4 }}>Transaction Registry</h1>
          <p className="muted" style={{ margin: 0 }}>Every movement across your synced accounts, categorized and searchable.</p>
        </div>
        <div className="row">
          <button className="btn btn-outline"><Icon name="download" size={15} />Export CSV</button>
        </div>
      </div>

      <div className="toolbar">
        <div className="search-box" style={{ maxWidth: 300 }}>
          <Icon name="search" size={16} />
          <input placeholder="Search merchants or categories" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <button className="tbtn"><Icon name="filter" size={15} />Filters</button>
      </div>

      {error && (
        <div className="card" style={{ background: '#FFF0F0', color: '#B04A3C', padding: '14px 18px', marginBottom: 14 }}>
          <b>Error:</b> {error}
          <button className="btn btn-outline" style={{ marginLeft: 12, padding: '4px 12px', fontSize: 12 }}
            onClick={() => { setError(null); window.location.reload() }}>Retry</button>
        </div>
      )}

      {loading ? (
        <div className="card" style={{ padding: '60px 20px', textAlign: 'center' }}>
          <div className="spinner" />
          <div className="muted" style={{ marginTop: 12 }}>Loading transactions…</div>
        </div>
      ) : rows.length === 0 && !error ? (
        <div className="card" style={{ padding: '60px 20px', textAlign: 'center' }}>
          <h4 className="muted">No transactions yet</h4>
          <p className="muted small">Upload a bank statement to get started.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'visible' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Date</th><th>Merchant</th><th>Category</th>
                  <th style={{ textAlign: 'right' }}>Amount</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.id}>
                    <td className="muted" style={{ whiteSpace: 'nowrap' }}>{r.date}</td>
                    <td>
                      <div className="merch">
                        <div className="m-ic" style={{ background: r.color, color: r.ink }}>{r.initial}</div>
                        <div>
                          <div style={{ fontWeight: 600 }}>{r.merchant}</div>
                          <small>{r.source_account}</small>
                        </div>
                      </div>
                    </td>
                    <td>
                      <CategoryChip row={r} open={openPicker === r.id}
                        onToggle={(id) => setOpenPicker(openPicker === id ? null : id)}
                        onSelect={changeCategory} />
                      {correcting === r.id && <span className="small muted" style={{ marginLeft: 6 }}>saving…</span>}
                    </td>
                    <td className="amount" style={{ color: r.direction === 'credit' ? 'var(--green)' : 'var(--ink)' }}>
                      {fmtAmount(r)}
                    </td>
                    <td><Pill status={r.status} /></td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={5} style={{ textAlign: 'center', padding: 30 }} className="muted">
                    No transactions match "{q}".
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="pager">
            <span className="small muted">
              Showing <b style={{ color: 'var(--ink)' }}>{filtered.length}</b> of <b style={{ color: 'var(--ink)' }}>{rows.length}</b> entries
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
