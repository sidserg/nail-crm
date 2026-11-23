import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'

// ---------------- Toasts ----------------
const ToastCtx = createContext(() => {})
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const push = useCallback((text, type = 'ok') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((t) => [...t, { id, text, type }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toasts">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`}>{t.text}</div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

// ---------------- Modal ----------------
export function Modal({ title, onClose, children, wide = false }) {
  useEffect(() => {
    const h = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    document.body.style.overflow = 'hidden'
    return () => { window.removeEventListener('keydown', h); document.body.style.overflow = '' }
  }, [onClose])
  return (
    <div className="overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className={`modal${wide ? ' wide' : ''}`}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="icon-btn" onClick={onClose} aria-label="Закрыть">✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}

// ---------------- Small bits ----------------
export const Spinner = () => <div className="spinner" />
export const PageLoading = () => <div className="page-loading"><Spinner /></div>
export const Empty = ({ children }) => <div className="empty">{children}</div>

export function Field({ label, children }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
    </div>
  )
}

export function Badge({ status }) {
  const s = { confirmed: ['Подтверждена', 'st-confirmed'], completed: ['Выполнена', 'st-completed'], cancelled: ['Отменена', 'st-cancelled'], no_show: ['Неявка', 'st-no_show'] }[status] || [status, '']
  return <span className={`badge ${s[1]}`}>{s[0]}</span>
}
