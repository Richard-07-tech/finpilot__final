import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Icon, Donut, AreaChart, Gauge, HeroArt, GradientCard, fmtMoney } from '../components/ui.jsx'
import { getMonthlySummary } from '../api.js'

const CATEGORY_COLORS = [
  '#D97B3F', '#E3A976', '#231E17', '#8A8B5C', '#C8BFA9', '#B8B58A',
  '#3E5C76', '#C0392B', '#2E86AB', '#7E7668',
]

function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [month] = useState(currentMonth)

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
          <div className="muted" style={{ marginTop: 14 }}>Loading financial data…</div>
        </section>
      </div>
    )
  }

  if (error) {
    return (
      <div className="stack">
        <section className="card" style={{ padding: '60px 20px', textAlign: 'center' }}>
          <div style={{ fontSize: 40, marginBottom: 10 }}>⚠</div>
          <h3 style={{ color: '#B04A3C' }}>Failed to load dashboard</h3>
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

  // Build category donut data
  const catTotals = data.category_totals || {}
  const totalExpenses = Object.values(catTotals).reduce((a, v) => a + parseFloat(v), 0)
  const donutData = Object.entries(catTotals)
    .sort(([, a], [, b]) => parseFloat(b) - parseFloat(a))
    .map(([label, amt], i) => ({
      label,
      amount: parseFloat(amt),
      pct: totalExpenses > 0 ? (parseFloat(amt) / totalExpenses) * 100 : 0,
      color: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
    }))

  const isEmpty = income === 0 && expenses === 0

  if (isEmpty) {
    return (
      <div className="stack">
        <section className="card hero">
          <div className="hero-grid">
            <div>
              <span className="eyebrow"><Icon name="spark" size={13} />Dashboard</span>
              <h1>No data for {month}</h1>
              <p className="hero-figures muted" style={{ maxWidth: 460 }}>
                Upload a bank statement or wait for transactions to appear for this month.
              </p>
              <Link to="/upload" className="btn btn-primary" style={{ marginTop: 16 }}>
                Upload Statement<Icon name="arrowRight" size={15} />
              </Link>
            </div>
            <div className="hero-art"><HeroArt /></div>
          </div>
        </section>
      </div>
    )
  }

  const stats = [
    { key: 'income', label: 'Total Income', value: income, delta: '', tone: 'up', sub: `${month}` },
    { key: 'expenses', label: 'Total Expenses', value: expenses, delta: '', tone: 'up', sub: `${month}` },
  ]

  const fmtCurrency = (n) => {
    const c = data.currency === 'INR' ? '₹' : '$'
    return `${c}${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  return (
    <div className="stack">
      {/* Hero */}
      <section className="card hero">
        <div className="hero-grid">
          <div>
            <span className="eyebrow"><Icon name="spark" size={13} />Financial Overview</span>
            <h1>Your {month} Summary</h1>
            <p className="hero-figures muted" style={{ maxWidth: 460 }}>
              Income of <b>{fmtCurrency(income)}</b> with expenses of{' '}
              <b>{fmtCurrency(expenses)}</b> — savings rate of <b>{savingsRate.toFixed(1)}%</b>.
            </p>
            <div className="net-box">
              <div>
                <div className="small muted">Net Savings ({month})</div>
                <div className="amt">{fmtCurrency(savings)}</div>
              </div>
              <Link to="/summary" className="btn btn-primary" style={{ marginLeft: 'auto' }}>
                Explore Details<Icon name="arrowRight" size={15} />
              </Link>
            </div>
          </div>
          <div className="hero-art"><HeroArt /></div>
        </div>
      </section>

      {/* Stat row */}
      <section className="grid4">
        {stats.map((s) => (
          <div key={s.key} className="card stat-card">
            <div className="stat-label">{s.label}</div>
            <div className="stat-value">{fmtCurrency(s.value)}</div>
            <div className="stat-sub">{s.sub}</div>
          </div>
        ))}
        <div className="card stat-card accent">
          <div className="row between">
            <div className="stat-label">Savings Rate</div>
            <span className="delta on-accent"><Icon name="spark" size={12} />{savingsRate.toFixed(1)}%</span>
          </div>
          <div className="stat-value">{savingsRate.toFixed(1)}%</div>
          <div className="stat-sub">of net income retained</div>
          <div className="progress-track"><div className="progress-fill" style={{ width: `${Math.min(savingsRate, 100)}%` }} /></div>
        </div>
        {data.anomaly_count > 0 && (
          <div className="card stat-card">
            <div className="stat-label">Anomalies</div>
            <div className="stat-value">{data.anomaly_count}</div>
            <div className="stat-sub">unusual transactions detected</div>
          </div>
        )}
      </section>

      {/* Spending breakdown */}
      {donutData.length > 0 && (
        <section className="grid2">
          <div className="card">
            <h3 className="section-title">Spending by Category</h3>
            <div className="small muted" style={{ marginBottom: 12 }}>Monthly distribution</div>
            <div style={{ textAlign: 'center' }}>
              <Donut data={donutData} size={170} thickness={22}
                centerTop={fmtCurrency(totalExpenses)} centerBottom="Total spend" />
            </div>
            <div className="cat-list">
              {donutData.slice(0, 5).map((c) => (
                <div key={c.label} className="cat-row">
                  <i style={{ background: c.color }} />{c.label}
                  <b>{fmtCurrency(c.amount)}</b>
                </div>
              ))}
              {donutData.length > 5 && (
                <div className="cat-row muted small">+ {donutData.length - 5} more categories</div>
              )}
            </div>
          </div>
          <div className="card">
            <h3 className="section-title">Efficiency</h3>
            <div className="small muted" style={{ marginBottom: 10 }}>Savings rate</div>
            <div className="row" style={{ gap: 18, justifyContent: 'center' }}>
              <Gauge pct={parseFloat(savingsRate.toFixed(1))} size={132} thickness={13} label="savings rate" />
              <div style={{ fontSize: 13 }}>
                <div className="muted small">Income</div>
                <div style={{ fontWeight: 700 }}>{fmtCurrency(income)}</div>
                <div className="muted small" style={{ marginTop: 10 }}>Expenses</div>
                <div style={{ fontWeight: 700 }}>{fmtCurrency(expenses)}</div>
                <div className="muted small" style={{ marginTop: 10 }}>Savings</div>
                <div style={{ fontWeight: 700 }}>{fmtCurrency(savings)}</div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Editorial summary */}
      <section className="card">
        <div className="editorial">
          <div>
            <span className="eyebrow plain">Summary</span>
            <h3 className="section-title" style={{ fontSize: 24, margin: '6px 0 12px' }}>Financial Overview</h3>
            <p>
              {month} closed with income of {fmtCurrency(income)} against {fmtCurrency(expenses)} in total outflow — a savings rate of {savingsRate.toFixed(1)}%.
              {donutData.length > 0 && ` Top spending category: ${donutData[0].label} at ${fmtCurrency(donutData[0].amount)}.`}
            </p>
            <Link to="/summary" className="link-arrow">View Full Monthly Report<Icon name="arrowRight" size={15} /></Link>
          </div>
          <GradientCard caption="Your finances, at a glance." height={220} />
        </div>
      </section>

      {/* Footer bar */}
      <section className="footer-bar">
        <span className="sync-dot" />
        <span className="small muted">
          Data for <b style={{ color: 'var(--ink)' }}>{month}</b> · {data.currency}
        </span>
        <div style={{ marginLeft: 'auto' }} className="row">
          <Link to="/upload" className="btn btn-outline"><Icon name="upload" size={15} />Upload Data</Link>
          <Link to="/summary" className="btn btn-primary"><Icon name="spark" size={15} />Full Report</Link>
        </div>
      </section>
    </div>
  )
}
