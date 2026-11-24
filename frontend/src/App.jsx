import React, { createContext, useContext, useEffect, useState } from 'react'
import { BrowserRouter, NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { api, getToken, setToken } from './api.js'
import { PageLoading, ToastProvider } from './ui.jsx'
import Login from './pages/Login.jsx'
import CalendarPage from './pages/CalendarPage.jsx'
import OverviewPage from './pages/OverviewPage.jsx'
import ClientsPage from './pages/ClientsPage.jsx'
import ServicesPage from './pages/ServicesPage.jsx'
import AnalyticsPage from './pages/AnalyticsPage.jsx'
import SettingsPage from './pages/SettingsPage.jsx'
import BookPage from './pages/BookPage.jsx'

export const SettingsCtx = createContext({ settings: null, refresh: () => {} })
export const useSettings = () => useContext(SettingsCtx)

const NAV = [
  { to: '/', label: 'Календарь', ico: '📅' },
  { to: '/overview', label: 'Обзор', ico: '👁️' },
  { to: '/clients', label: 'Клиенты', ico: '👥' },
  { to: '/analytics', label: 'Финансы', ico: '📊' },
  { to: '/services', label: 'Услуги', ico: '💅' },
  { to: '/settings', label: 'Настройки', ico: '⚙️' },
]

function Layout({ children }) {
  const { settings } = useSettings()
  const nav = useNavigate()
  const logout = () => { setToken(null); nav('/login') }
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo">💅</span>
          <div>
            <div className="name">{settings.salon_name}</div>
            <div className="sub">Nail CRM</div>
          </div>
        </div>
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
            <span>{n.ico}</span>{n.label}
          </NavLink>
        ))}
        <div className="spacer" />
        <button className="btn ghost" onClick={logout}>Выйти</button>
      </aside>
      <main className="main">{children}</main>
      <nav className="bottomnav">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}>
            <span className="ico">{n.ico}</span>{n.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}

function Private() {
  const [settings, setSettings] = useState(null)
  const nav = useNavigate()
  const token = getToken()

  useEffect(() => {
    if (!token) { nav('/login', { replace: true }); return }
    api('/settings').then(setSettings).catch(() => {})
  }, [token])

  if (!token) return null
  if (!settings) return <PageLoading />

  return (
    <SettingsCtx.Provider value={{ settings, refresh: () => api('/settings').then(setSettings) }}>
      <Layout>
        <Routes>
          <Route path="/" element={<CalendarPage />} />
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/clients" element={<ClientsPage />} />
          <Route path="/services" element={<ServicesPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </SettingsCtx.Provider>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/book" element={<BookPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<Private />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}
