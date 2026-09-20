import React, { useEffect, useState } from 'react'
import { Icon, AreaChart, Pill, GradientCard } from '../components/ui.jsx'
import { getMonthlySummary } from '../api.js'

const CATEGORY_COLORS = [
  '#D97B3F', '#E3A976', '#231E17', '#8A8B5C', '#C8BFA9', '#B8B58A',
  '#3E5C76', '#C0392B', '#2E86AB', '#7E7668',
]

function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function prevMonth(monthStr) {
  const [y, m] = monthStr.split('-').map(Number)
  const prev = m === 1 ? `${y - 1}-12` : `${y}-${String(m - 1).padStart(2, '0')}`
  return prev
}

function monthLabel(monthStr) {
  const [y, m] = monthStr.split('-').map(Number)
  const d = new Date(y, m - 1)
  return d.toLocaleString('en-US', { month: 'long', year: 'numeric' })
}

export default function MonthlySummary() {
  const [month] = useState(currentMonth)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    getMonthlySummary(month)
      .then((d) => { if (!cancelled) setData(d) })
      .catch((e) => { if (!cancelled) setError(e.message) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [month])

  if (loading) {
    return (
      <div className="stack">
        <section className="card" style={{ padding: '80px 20px', textAlign: 'center' }}>
          <div className="spinner" />
          <div className="muted" style={{ marginTop: 14 }}>Loading monthly report…</div>
        </section>
      </div>
    )
  }

  if (error) {
    return (
      <div className="stack">
        <section className="card" style={{ padding: '60px 20px', textAlign: 'center' }}>
          <div style={{ fontSize: 40, marginBottom: 10 }}>⚠</div>
          <h3 style={{ color: '#B04A3C' }}>Failed to load report</h3>
          <p className="muted">{error}</p>
          <button className="btn btn-primary" onClick={() => window.location.reload()}>Retry</button>
        </section>
      </div>
    )
  }

  const income = parseFloat(data.income) || 0
  const expenses = parseFloat(data.expenses) || 0
  const savings = income - expenses
  const rawRate = data.savings_rate != null ? data.savings_rate : (income > 0 ? (savings / income) : 0)
  const savingsRate = Math.abs(rawRate) <= 1 ? rawRate * 100 : rawRate

  const fmtCurrency = (n) => {
    const c = data.currency === 'INR' ? '₹' : '$'
    return `${c}${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const isEmpty = income === 0 && expenses === 0

  // Top categories for display
  const topCats = (data.top_categories || []).map((tc, i) => ({
    category: tc.category,
    amount: parseFloat(tc.amount),
    color: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
  }))

  const catTotals = data.category_totals || {}
  const catEntries = Object.entries(catTotals)
    .sort(([, a], [, b]) => parseFloat(b) - parseFloat(a))
    .map(([cat, amt], i) => ({
      name: cat,
      amount: parseFloat(amt),
      color: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
    }))

  const stats = [
    { label: 'Total Spending', value: fmtCurrency(expenses), sub: month, tone: 'up' },
    { label: 'Total Income', value: fmtCurrency(income), sub: month, tone: 'up' },
    { label: 'Savings Rate', value: `${savingsRate.toFixed(1)}%`, sub: `Net savings: ${fmtCurrency(savings)}`, tone: 'up' },
    { label: 'Recurring Total', value: fmtCurrency(parseFloat(data.recurring_total) || 0), sub: 'Detected subscriptions', tone: 'neutral' },
  ]

  return (
    <div className="stack">
      {/* Report header */}
      <section className="card hero">
        <div className="hero-grid">
          <div>
            <div className="row" style={{ gap: 10, flexWrap: 'wrap' }}>
              <span className="eyebrow">Monthly Report</span>
              <span className="small muted">{monthLabel(month)}</span>
            </div>
            <h1 className="serif" style={{ fontStyle: 'italic', fontSize: 38, margin: '16px 0 12px', lineHeight: 1.15 }}>
              {isEmpty ? 'No data this month' : `${monthLabel(month)} in Review`}
            </h1>
            {isEmpty ? (
              <p className="muted" style={{ maxWidth: 520 }}>
                No transactions were found for this period. Upload a statement to see your summary.
              </p>
            ) : (
              <p className="muted" style={{ maxWidth: 520 }}>
                Income of {fmtCurrency(income)} against {fmtCurrency(expenses)} in expenses.
                Savings rate: {savingsRate.toFixed(1)}%.
                {data.anomaly_count > 0 && ` ${data.anomaly_count} anomal${data.anomaly_count === 1 ? 'y' : 'ies'} detected.`}
              </p>
            )}
          </div>
          <GradientCard caption={`${monthLabel(month)}, in review.`} height={230} />
        </div>
      </section>

      {!isEmpty && (
        <>
          {/* Stat row */}
          <section className="grid4">
            {stats.map((s) => (
              <div key={s.label} className="card stat-card">
                <div className="stat-label">{s.label}</div>
                <div className="stat-value">{s.value}</div>
                <span className={`delta ${s.tone === 'neutral' ? 'neutral' : s.tone}`}>{s.sub}</span>
              </div>
            ))}
          </section>

          {/* Category breakdown */}
          {catEntries.length > 0 && (
            <section className="card">
              <h3 className="section-title">Spending by Category</h3>
              <div className="small muted" style={{ marginBottom: 12 }}>Category breakdown for {month}</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
                {catEntries.map((c) => (
                  <div key={c.name} className="cat-row" style={{ padding: '8px 0' }}>
                    <i style={{ background: c.color }} />{c.name}
                    <b style={{ marginLeft: 'auto' }}>{fmtCurrency(c.amount)}</b>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Anomalies */}
          {data.anomaly_count > 0 && (
            <section>
              <h3 className="section-title" style={{ marginBottom: 4 }}>Anomalies Detected</h3>
              <div className="small muted" style={{ marginBottom: 14 }}>
                {data.anomaly_count} unusual transaction{data.anomaly_count !== 1 ? 's' : ''} found this month
              </div>
              <div className="card var-card" style={{ maxWidth: 400 }}>
                <div className="row between">
                  <div className="var-ic" style={{ background: 'var(--amber-soft)', color: '#96691C' }}>
                    <Icon name="alert" size={19} />
                  </div>
                  <span className="serif" style={{ fontSize: 19, fontWeight: 600 }}>{data.anomaly_count}</span>
                </div>
                <div style={{ fontWeight: 700 }}>Unusual Transactions</div>
                <p className="small muted" style={{ margin: 0 }}>
                  Review your transaction list for details on flagged items.
                </p>
              </div>
            </section>
          )}
        </>
      )}

      {/* Editorial closing */}
      <section className="card" style={{ padding: '46px 30px' }}>
        <p className="pull-quote">
          {isEmpty
            ? '"Every financial journey starts with a single statement. Upload your data and let the numbers tell their story."'
            : `"${monthLabel(month)} showed ${savingsRate > 0 ? 'positive momentum' : 'room for improvement'} with a ${savingsRate.toFixed(1)}% savings rate. ${catEntries.length > 0 ? `${catEntries[0].name} led spending at ${fmtCurrency(catEntries[0].amount)}.` : ''}"`
          }
        </p>
        <div className="sig">— FinPilot Analytics</div>
      </section>
    </div>
  )
}
