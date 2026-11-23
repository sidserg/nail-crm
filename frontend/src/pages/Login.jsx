import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setToken } from '../api.js'
import { Field, useToast } from '../ui.jsx'

export default function Login() {
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [config, setConfig] = useState(null)
  const [busy, setBusy] = useState(false)
  const nav = useNavigate()
  const toast = useToast()

  useEffect(() => { api('/public/config').then(setConfig).catch(() => {}) }, [])

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const res = await api('/auth/login', { method: 'POST', body: { login, password } })
      setToken(res.token)
      nav('/', { replace: true })
    } catch (err) {
      toast(err.message, 'err')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <div className="logo">💅</div>
        <h1>{config ? config.salon_name : 'Nail CRM'}</h1>
        <div className="sub">Кабинет мастера: календарь, клиенты, финансы</div>
        <Field label="Логин">
          <input className="input" value={login} onChange={(e) => setLogin(e.target.value)} autoFocus autoComplete="username" />
        </Field>
        <Field label="Пароль">
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
        </Field>
        <button className="btn block" disabled={busy || !login || !password}>Войти</button>
        {config && config.demo && (
          <div className="demo-hint">Демо-доступ: логин <b>admin</b>, пароль <b>admin123</b></div>
        )}
      </form>
    </div>
  )
}
