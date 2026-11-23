import React, { useState } from 'react'
import { api, copyText } from '../api.js'
import { useSettings } from '../App.jsx'
import { Field, useToast } from '../ui.jsx'
import { WEEKDAYS } from '../utils.js'

export default function SettingsPage() {
  const { settings, refresh } = useSettings()
  const toast = useToast()
  const [form, setForm] = useState({ ...settings })
  const [busy, setBusy] = useState(false)
  const [pw, setPw] = useState({ old: '', next: '', repeat: '' })

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const workDays = (form.work_days || '').split(',').filter(Boolean)
  const toggleDay = (i) => {
    const s = new Set(workDays)
    s.has(String(i)) ? s.delete(String(i)) : s.add(String(i))
    setForm({ ...form, work_days: [...s].sort().join(',') })
  }

  const save = async () => {
    setBusy(true)
    try {
      await api('/settings', { method: 'PUT', body: form })
      await refresh()
      toast('Настройки сохранены')
    } catch (e) { toast(e.message, 'err') } finally { setBusy(false) }
  }

  const bookUrl = `${location.origin}/book`
  const copyLink = async () => {
    (await copyText(bookUrl)) ? toast('Ссылка скопирована') : toast('Не удалось скопировать', 'err')
  }

  const changePassword = async () => {
    if (pw.next !== pw.repeat) { toast('Новые пароли не совпадают', 'err'); return }
    try {
      await api('/auth/change-password', { method: 'POST', body: { old_password: pw.old, new_password: pw.next } })
      setPw({ old: '', next: '', repeat: '' })
      toast('Пароль изменён')
    } catch (e) { toast(e.message, 'err') }
  }

  return (
    <div>
      <h2 className="page-title">Настройки</h2>

      <div className="card">
        <h3>Онлайн-запись для клиентов 🌐</h3>
        <div className="small muted mb">Отправьте эту ссылку клиентам или разместите в шапке профиля соцсетей. Клиент видит только свободные окна и записывается сам — запись мгновенно появляется в вашем календаре.</div>
        <div className="copy-row">
          <input className="input" readOnly value={bookUrl} onFocus={(e) => e.target.select()} />
          <button className="btn sm secondary shrink" onClick={copyLink}>Копировать</button>
          <a className="btn sm ghost shrink" href={bookUrl} target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}>Открыть</a>
        </div>
      </div>

      <div className="card">
        <h3>Салон и расписание</h3>
        <div className="row">
          <Field label="Название студии"><input className="input" value={form.salon_name} onChange={set('salon_name')} /></Field>
          <Field label="Адрес (виден при онлайн-записи)"><input className="input" value={form.salon_address} onChange={set('salon_address')} placeholder="ул. Пример, 1" /></Field>
        </div>
        <div className="row">
          <Field label="Начало дня"><input className="input" type="time" value={form.work_start} onChange={set('work_start')} /></Field>
          <Field label="Конец дня"><input className="input" type="time" value={form.work_end} onChange={set('work_end')} /></Field>
          <Field label="Шаг сетки">
            <select className="input" value={form.slot_step} onChange={set('slot_step')}>
              {[10, 15, 20, 30, 60].map((s) => <option key={s} value={s}>{s} мин</option>)}
            </select>
          </Field>
        </div>
        <Field label="Рабочие дни">
          <div className="status-btns">
            {WEEKDAYS.map((d, i) => (
              <button key={d} type="button" className={'st-confirmed' + (workDays.includes(String(i)) ? ' active' : '')} onClick={() => toggleDay(i)}>{d}</button>
            ))}
          </div>
        </Field>
        <div className="row">
          <Field label="Горизонт онлайн-записи, дней"><input className="input" type="number" min="1" max="90" value={form.booking_horizon_days} onChange={set('booking_horizon_days')} /></Field>
          <Field label="Мин. время до онлайн-записи, мин"><input className="input" type="number" min="0" max="1440" value={form.min_lead_minutes} onChange={set('min_lead_minutes')} /></Field>
        </div>
        <button className="btn" disabled={busy} onClick={save}>Сохранить настройки</button>
      </div>

      <div className="card">
        <h3>Telegram-напоминания 🤖</h3>
        {settings.telegram_enabled ? (
          <div>
            <div className="tg-status on">✅ Бот подключён{settings.bot_username ? <>: <a href={`https://t.me/${settings.bot_username}`} target="_blank" rel="noreferrer">@{settings.bot_username}</a></> : null}</div>
            <div className="small muted mt">
              Клиент подключается по персональной ссылке из его карточки (раздел «Клиенты»). Бот напомнит о визите за 24 часа и за 2 часа с кнопками «Подтверждаю» / «Отменить». Отмена через бота мгновенно освобождает слот.
            </div>
          </div>
        ) : (
          <div className="small muted">
            Бот не настроен. Создайте бота у <b>@BotFather</b>, укажите <code>TELEGRAM_BOT_TOKEN</code> и <code>TELEGRAM_OWNER_CHAT_ID</code> в файле <code>.env</code> на сервере и перезапустите контейнеры: <code>docker compose up -d</code>. Подробная инструкция — в README проекта.
          </div>
        )}
      </div>

      <div className="card">
        <h3>Безопасность 🔒</h3>
        <div className="row">
          <Field label="Текущий пароль"><input className="input" type="password" value={pw.old} onChange={(e) => setPw({ ...pw, old: e.target.value })} autoComplete="current-password" /></Field>
          <Field label="Новый пароль"><input className="input" type="password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} autoComplete="new-password" /></Field>
          <Field label="Повторите новый"><input className="input" type="password" value={pw.repeat} onChange={(e) => setPw({ ...pw, repeat: e.target.value })} autoComplete="new-password" /></Field>
        </div>
        <button className="btn secondary" disabled={!pw.old || pw.next.length < 6} onClick={changePassword}>Сменить пароль</button>
      </div>
    </div>
  )
}
