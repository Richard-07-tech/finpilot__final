import React from 'react'

export const fmtMoney = (n, opts = {}) =>
  (n < 0 ? '-$' : '$') +
  Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2, ...opts })

// ---------- Icons ----------
const P = {
  grid: <><rect x="3.5" y="3.5" width="7" height="7" rx="1.5" /><rect x="13.5" y="3.5" width="7" height="7" rx="1.5" /><rect x="3.5" y="13.5" width="7" height="7" rx="1.5" /><rect x="13.5" y="13.5" width="7" height="7" rx="1.5" /></>,
  chat: <path d="M4 6.5A3.5 3.5 0 0 1 7.5 3h9A3.5 3.5 0 0 1 20 6.5v6a3.5 3.5 0 0 1-3.5 3.5H9.5L4 20V6.5Z" />,
  report: <><path d="M6 3h8l4 4v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" /><path d="M14 3v4h4" /><path d="M9 12.5h6M9 16.5h6" /></>,
  upload: <><path d="M12 15V4.5" /><path d="m7.5 9 4.5-4.5L16.5 9" /><path d="M4 15v3a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3v-3" /></>,
  list: <><path d="M9 6h11M9 12h11M9 18h11" /><circle cx="4.5" cy="6" r="1" /><circle cx="4.5" cy="12" r="1" /><circle cx="4.5" cy="18" r="1" /></>,
  settings: <><path d="M4 7h16M4 12h16M4 17h16" /><circle cx="9" cy="7" r="2" fill="#FCFAF5" /><circle cx="15" cy="12" r="2" fill="#FCFAF5" /><circle cx="8" cy="17" r="2" fill="#FCFAF5" /></>,
  bell: <><path d="M6 9.5a6 6 0 0 1 12 0c0 3.8 1.4 5.2 2 5.7H4c.6-.5 2-1.9 2-5.7Z" /><path d="M10 19a2 2 0 0 0 4 0" /></>,
  search: <><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4.5 4.5" /></>,
  download: <><path d="M12 4v10.5" /><path d="m7.5 10.5 4.5 4.5 4.5-4.5" /><path d="M4 19.5h16" /></>,
  share: <><circle cx="6" cy="12" r="2.5" /><circle cx="17.5" cy="5.5" r="2.5" /><circle cx="17.5" cy="18.5" r="2.5" /><path d="m8.3 10.8 6.9-4M8.3 13.2l6.9 4" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  arrowRight: <path d="M4 12h15m-6-6 6 6-6 6" />,
  check: <path d="m5 12.5 4.5 4.5L19 7.5" />,
  alert: <><path d="M12 4.5 3.5 19.5h17L12 4.5Z" /><path d="M12 10v4.2" /><circle cx="12" cy="16.8" r=".4" fill="currentColor" /></>,
  flag: <><path d="M6 21V4" /><path d="M6 5c2.5-1.6 5-1.6 7.5 0s5 1.6 6.5.8v8c-1.5.8-4 .8-6.5-.8S8.5 11.4 6 13" /></>,
  shield: <><path d="M12 3 5.5 5.8v5.4c0 4.3 2.8 7.6 6.5 9.8 3.7-2.2 6.5-5.5 6.5-9.8V5.8L12 3Z" /><path d="m9.2 11.6 2 2 3.8-3.8" /></>,
  spark: <path d="M12 3.5 14 10l6.5 2-6.5 2-2 6.5L10 14l-6.5-2L10 10l2-6.5Z" />,
  dots: <><circle cx="5" cy="12" r="1.3" fill="currentColor" stroke="none" /><circle cx="12" cy="12" r="1.3" fill="currentColor" stroke="none" /><circle cx="19" cy="12" r="1.3" fill="currentColor" stroke="none" /></>,
  chevronDown: <path d="m6 9.5 6 6 6-6" />,
  calendar: <><rect x="4" y="5.5" width="16" height="15" rx="2.5" /><path d="M4 10.5h16M8.5 3.5v4M15.5 3.5v4" /></>,
  filter: <path d="M4 6.5h16M7.5 12h9M10.5 17.5h3" />,
  send: <path d="M5 12h13m0 0-5-5m5 5-5 5" />,
  x: <path d="M6 6l12 12M18 6 6 18" />,
  logout: <><path d="M15.5 8.5 20 12l-4.5 3.5" /><path d="M20 12H9" /><path d="M9 5H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h3" /></>,
}

export function Icon({ name, size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {P[name]}
    </svg>
  )
}

// ---------- Status pill ----------
const PILL_TONE = {
  Completed: 'green', Active: 'green', Renewed: 'green',
  Pending: 'amber', Upcoming: 'amber',
  Flagged: 'gray', Uncategorized: 'gray',
}
export function Pill({ status }) {
  const tone = PILL_TONE[status] || 'gray'
  return <span className={`pill ${tone}`}><span className="pdot" />{status}</span>
}

// ---------- Donut chart ----------
export function Donut({ data, size = 190, thickness = 24, centerTop, centerBottom }) {
  const r = (size - thickness) / 2
  const c = 2 * Math.PI * r
  let acc = 0
  return (
    <div className="donut-wrap" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#F1EBDD" strokeWidth={thickness} />
        <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
          {data.map((d) => {
            const len = (c * d.pct) / 100
            const el = (
              <circle key={d.label} cx={size / 2} cy={size / 2} r={r} fill="none"
                stroke={d.color} strokeWidth={thickness}
                strokeDasharray={`${Math.max(len - 2, 1)} ${c - len + 2}`}
                strokeDashoffset={-acc} />
            )
            acc += len
            return el
          })}
        </g>
      </svg>
      <div className="donut-center">
        <div className="big">{centerTop}</div>
        {centerBottom && <div className="small muted">{centerBottom}</div>}
      </div>
    </div>
  )
}

// ---------- Area / line chart ----------
function smoothPath(pts) {
  if (pts.length < 2) return ''
  let d = `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)]
    const c1x = p1.x + (p2.x - p0.x) / 6, c1y = p1.y + (p2.y - p0.y) / 6
    const c2x = p2.x - (p3.x - p1.x) / 6, c2y = p2.y - (p3.y - p1.y) / 6
    d += ` C ${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`
  }
  return d
}

export function AreaChart({ months, series, height = 250, idPrefix = 'ac' }) {
  const W = 660, H = height, pad = { l: 6, r: 10, t: 14, b: 28 }
  const max = Math.max(...series.flatMap((s) => s.data)) * 1.18
  const x = (i) => pad.l + (i * (W - pad.l - pad.r)) / (months.length - 1)
  const y = (v) => pad.t + (1 - v / max) * (H - pad.t - pad.b)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
      <defs>
        {series.map((s, si) => (
          <linearGradient key={si} id={`${idPrefix}-g${si}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={s.color} stopOpacity="0.28" />
            <stop offset="100%" stopColor={s.color} stopOpacity="0.02" />
          </linearGradient>
        ))}
      </defs>
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <line key={f} x1={pad.l} x2={W - pad.r} y1={pad.t + (1 - f) * (H - pad.t - pad.b)} y2={pad.t + (1 - f) * (H - pad.t - pad.b)}
          stroke="#F0E9DB" strokeWidth="1" />
      ))}
      {series.map((s, si) => {
        const pts = s.data.map((v, i) => ({ x: x(i), y: y(v) }))
        const line = smoothPath(pts)
        const area = `${line} L ${pts[pts.length - 1].x.toFixed(1)} ${H - pad.b} L ${pts[0].x.toFixed(1)} ${H - pad.b} Z`
        return (
          <g key={s.name}>
            <path d={area} fill={`url(#${idPrefix}-g${si})`} />
            <path d={line} fill="none" stroke={s.color} strokeWidth="2.4" strokeLinecap="round" />
            {pts.map((p, i) => (
              <circle key={i} cx={p.x} cy={p.y} r="3.2" fill="#fff" stroke={s.color} strokeWidth="2" />
            ))}
          </g>
        )
      })}
      {months.map((m, i) => (
        <text key={m} x={x(i)} y={H - 8} textAnchor="middle" fontSize="11" fill="#A79E8F">{m}</text>
      ))}
    </svg>
  )
}

// ---------- Gauge ring ----------
export function Gauge({ pct, size = 150, thickness = 14, label }) {
  const r = (size - thickness) / 2
  const c = 2 * Math.PI * r
  const len = (c * Math.min(pct, 100)) / 100
  return (
    <div className="donut-wrap" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#F1EBDD" strokeWidth={thickness} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#D97B3F" strokeWidth={thickness}
          strokeLinecap="round" strokeDasharray={`${len} ${c - len}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      </svg>
      <div className="donut-center">
        <div className="big serif">{pct}%</div>
        {label && <div className="small muted">{label}</div>}
      </div>
    </div>
  )
}

// ---------- Decorative organic illustrations ----------
export function HeroArt() {
  return (
    <svg viewBox="0 0 280 210" style={{ width: '100%', maxWidth: 300, height: 'auto' }} aria-hidden="true">
      <circle cx="140" cy="105" r="96" fill="#F3E7D2" />
      <circle cx="140" cy="105" r="96" fill="none" stroke="#E7D9BF" strokeWidth="1.5" strokeDasharray="2 6" />
      <path d="M78 176 v-64 a32 32 0 0 1 64 0 v64 Z" fill="#D97B3F" />
      <path d="M142 176 v-42 a23 23 0 0 1 46 0 v42 Z" fill="#8A8B5C" opacity=".92" />
      <path d="M188 176 v-26 a15 15 0 0 1 30 0 v26 Z" fill="#E3A976" />
      <path d="M62 176 h160" stroke="#231E17" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="222" cy="52" r="15" fill="#E3A976" />
      <circle cx="222" cy="52" r="24" fill="none" stroke="#E3A976" strokeWidth="1.5" opacity=".5" />
      <path d="M52 66 q12 -22 30 -16" stroke="#8A8B5C" strokeWidth="3.5" fill="none" strokeLinecap="round" />
      <path d="M54 82 q18 -8 28 5" stroke="#8A8B5C" strokeWidth="3.5" fill="none" strokeLinecap="round" />
      <circle cx="98" cy="44" r="3" fill="#D97B3F" />
      <circle cx="246" cy="120" r="3" fill="#8A8B5C" />
      <circle cx="34" cy="128" r="3" fill="#E3A976" />
    </svg>
  )
}

export function ShieldArt({ size = 64 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 72 72" aria-hidden="true">
      <circle cx="36" cy="36" r="34" fill="#F6E4D2" />
      <path d="M36 16 20 23v11c0 9 6.5 15.5 16 20 9.5-4.5 16-11 16-20V23L36 16Z" fill="#D97B3F" />
      <path d="M36 22 25 27v8c0 6.6 4.8 11.4 11 14.6 6.2-3.2 11-8 11-14.6v-8L36 22Z" fill="#F7F4EE" />
      <path d="m30.5 35.5 4 4 7.5-7.5" fill="none" stroke="#8A8B5C" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function EmptyArt({ size = 72 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 80 80" aria-hidden="true">
      <circle cx="40" cy="40" r="36" fill="#F1EBDD" />
      <path d="M24 52 v-14 a10 10 0 0 1 20 0 v14 Z" fill="#E3A976" />
      <circle cx="47" cy="30" r="9" fill="none" stroke="#8A8B5C" strokeWidth="3" />
      <path d="m53.5 36.5 6 6" stroke="#8A8B5C" strokeWidth="3" strokeLinecap="round" />
      <path d="M20 60 h40" stroke="#C8BFA9" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  )
}

export function DropArt({ size = 84 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 96 96" aria-hidden="true">
      <circle cx="48" cy="48" r="44" fill="#F3E7D2" />
      <path d="M30 68 V44 a18 18 0 0 1 36 0 V68 Z" fill="#D97B3F" opacity=".9" />
      <path d="M48 58 V34" stroke="#F7F4EE" strokeWidth="4" strokeLinecap="round" />
      <path d="m40 42 8-8 8 8" fill="none" stroke="#F7F4EE" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="74" cy="26" r="6" fill="#8A8B5C" />
      <path d="M18 30 q8 -12 18 -9" stroke="#8A8B5C" strokeWidth="3" fill="none" strokeLinecap="round" />
      <path d="M22 74 h52" stroke="#231E17" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  )
}

export function GradientCard({ caption, height = 200 }) {
  return (
    <div className="gradient-card" style={{ minHeight: height }}>
      <svg viewBox="0 0 300 160" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} aria-hidden="true">
        <circle cx="238" cy="34" r="52" fill="rgba(255,255,255,.14)" />
        <path d="M30 150 v-40 a22 22 0 0 1 44 0 v40 Z" fill="rgba(255,255,255,.18)" />
        <path d="M86 150 v-26 a14 14 0 0 1 28 0 v26 Z" fill="rgba(35,30,23,.18)" />
        <path d="M196 62 q14 -26 34 -20" stroke="rgba(255,255,255,.5)" strokeWidth="4" fill="none" strokeLinecap="round" />
        <path d="M200 82 q20 -10 32 6" stroke="rgba(255,255,255,.4)" strokeWidth="4" fill="none" strokeLinecap="round" />
      </svg>
      <div className="cap serif">{caption}</div>
    </div>
  )
}
