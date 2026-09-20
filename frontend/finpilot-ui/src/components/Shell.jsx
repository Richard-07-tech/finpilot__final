import React from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Icon } from './ui.jsx'
import { navItems } from '../data/mock.js'
import { useSession } from '../context/SessionContext.jsx'

function BrandMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 20 V12 a8 8 0 0 1 16 0 V20 Z" fill="#F7F4EE" />
      <path d="M9.5 20 v-4.5 a2.5 2.5 0 0 1 5 0 V20 Z" fill="#BC6027" />
    </svg>
  )
}

export default function Shell() {
  const { pathname } = useLocation()
  const { session, resetSession } = useSession()

  const displayName  = session?.displayName ?? 'You'
  const initials     = displayName.slice(0, 2).toUpperCase()
  const current      = navItems.find((n) => n.to === pathname) || navItems[0]

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><BrandMark /></div>
          <div className="txt">
            <div className="brand-name">Vantage</div>
            <div className="brand-sub">Finance</div>
          </div>
        </div>
        <div className="nav-label txt">Menu</div>
        <nav>
          {navItems.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === '/dashboard'}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
              <Icon name={n.icon} size={18} />
              <span className="txt">{n.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          {/* Settings (placeholder) */}
          <div className="nav-item" style={{ cursor: 'pointer' }}>
            <Icon name="settings" size={18} />
            <span className="txt">Settings</span>
          </div>
          {/* Session user chip */}
          <div className="user-chip">
            <div className="avatar orange">{initials}</div>
            <div className="txt" style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {displayName}
              </div>
              <div className="small muted">Demo session</div>
            </div>
          </div>
          {/* Start Over */}
          <button
            id="start-over-btn"
            className="start-over-btn"
            onClick={resetSession}
            title="Clear this session and return to the welcome screen"
          >
            <Icon name="logout" size={14} />
            Start Over
          </button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="crumb">Vantage / <b>{current.crumb}</b></div>
          <div className="search-box">
            <Icon name="search" size={16} />
            <input placeholder="Search transactions, reports, merchants..." />
          </div>
          <button className="icon-btn" aria-label="Notifications" style={{ marginLeft: 'auto' }}>
            <Icon name="bell" size={17} />
            <span className="dot" />
          </button>
          <div className="topbar-user" style={{ marginLeft: 0 }}>
            <div className="who" style={{ textAlign: 'right' }}>
              <div className="nm">Hi, {displayName}</div>
              <div className="plan">Demo session</div>
            </div>
            <div className="avatar orange">{initials}</div>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
