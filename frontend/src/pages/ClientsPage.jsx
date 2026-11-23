import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, copyText } from '../api.js'
import { useSettings } from '../App.jsx'
import { Badge, Empty, Field, Modal, PageLoading, useToast } from '../ui.jsx'
import { fmtPhone, money, ruDate, ruDateTime } from '../utils.js'

function ClientModal({ clientId, onClose, onChanged }) {
  const isNew = !clientId
  const { settings } = useSettings()
  const toast = useToast()
  const nav = useNavigate()
  const [detail, setDetail] = useState(null)
  const [form, setForm] = useState({ name: '', phone: '', birth_date: '', notes: '' })
  const [busy, setBusy] = useState(false)

  const load = () => {
    if (!clientId) return
    api(`/clients/${clientId}`).then((d) => {
      setDetail(d)
      setForm({
        name: d.client.name,
        phone: fmtPhone(d.client.phone),
        birth_date: d.client.birth_date || '',
        notes: d.client.notes || '',
      })
    }).catch((e) => toast(e.message, 'err'))
  }
  useEffect(load, [clientId])

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const save = async () => {
    setBusy(true)
    try {
      const body = { name: form.name, phone: form.phone, birth_date: form.birth_date || null, notes: form.notes }
      if (isNew) {
        await api('/clients', { method: 'POST', body })
        toast('Клиент добавлен')
        onChanged()
        onClose()
      } else {
        await api(`/clients/${clientId}`, { method: 'PATCH', body })
        toast('Сохранено')
        onChanged()
        load()
      }
    } catch (e) { toast(e.message, 'err') } finally { setBusy(false) }
  }

  const remove = async () => {
    if (!confirm(`Удалить клиента «${form.name}»?`)) return
    try {
      await api(`/clients/${clientId}`, { method: 'DELETE' })
    } catch (e) {
      if (e.status === 409) {
        if (!confirm(e.message + '\n\nУдалить клиента ВМЕСТЕ со всеми записями?')) return
        try { await api(`/clients/${clientId}`, { method: 'DELETE', params: { force: true } }) }
        catch (e2) { toast(e2.message, 'err'); return }
      } else { toast(e.message, 'err'); return }
    }
    toast('Клиент удалён')
    onChanged()
    onClose()
  }

  const tgLink = detail && settings.bot_username
    ? `https://t.me/${settings.bot_username}?start=c_${detail.client.tg_token}`
    : null

  const copyTg = async () => {
    (await copyText(tgLink)) ? toast('Ссылка скопирована — отправьте её клиенту') : toast('Не удалось скопировать', 'err')
  }

  return (
    <Modal title={isNew ? 'Новый клиент' : 'Карточка клиента'} onClose={onClose} wide>
      {detail === null && !isNew ? <PageLoading /> : (
        <div>
          {detail && (
            <div className="cal-summary">
              <span className="sum-chip">Визитов: <b>{detail.stats.visits}</b></span>
              <span className="sum-chip">Потрачено: <b>{money(detail.stats.total_spent)}</b></span>
              <span className="sum-chip">Последний визит: <b>{detail.stats.last_visit ? ruDateTime(detail.stats.last_visit) : '—'}</b></span>
            </div>
          )}
          <div className="row">
            <Field label="Имя">
              <input className="input" value={form.name} onChange={set('name')} />
            </Field>
            <Field label="Телефон">
              <input className="input" value={form.phone} onChange={set('phone')} inputMode="tel" placeholder="+7 …" />
            </Field>
          </div>
          <Field label="Дата рождения">
            <input className="input" type="date" value={form.birth_date} onChange={set('birth_date')} />
          </Field>
          <Field label="Заметки (аллергии, предпочтения по дизайну/цвету)">
            <textarea className="input" value={form.notes} onChange={set('notes')} rows={3} />
          </Field>

          {detail && settings.telegram_enabled && (
            <Field label="Напоминания в Telegram">
              <div className="copy-row">
                <input className="input" readOnly value={tgLink || ''} onFocus={(e) => e.target.select()} />
                <button className="btn sm secondary shrink" onClick={copyTg}>Копировать</button>
              </div>
              <div className={'tg-status ' + (detail.client.telegram_chat_id ? 'on' : 'off')}>
                {detail.client.telegram_chat_id
                  ? '✅ Клиент подключил бота — напоминания придут за 24 ч и за 2 ч'
                  : '○ Отправьте ссылку клиенту: он нажмёт «Старт» в боте и подключит напоминания'}
              </div>
            </Field>
          )}

          <div className="flex-between mt">
            {!isNew ? <button className="btn danger" onClick={remove}>Удалить</button> : <span />}
            <div style={{ display: 'flex', gap: 8 }}>
              {!isNew && (
                <button className="btn secondary" onClick={() => nav(`/?client=${clientId}`)}>📅 Записать</button>
              )}
              <button className="btn" disabled={busy || !form.name.trim() || !form.phone.trim()} onClick={save}>Сохранить</button>
            </div>
          </div>

          {detail && detail.appointments.length > 0 && (
            <div className="mt">
              <h3 style={{ fontSize: 14, margin: '16px 0 4px' }}>История посещений</h3>
              {detail.appointments.slice(0, 20).map((a) => (
                <div key={a.id} className="history-item">
                  <div>
                    <b>{ruDateTime(a.start_at)}</b> · {a.service.name}
                    {a.source === 'online' ? ' 🌐' : ''}
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span>{money(a.price)}</span>
                    <Badge status={a.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}

export default function ClientsPage() {
  const [q, setQ] = useState('')
  const [list, setList] = useState(null)
  const [sel, setSel] = useState(null) // {id} | {isNew:true}
  const toast = useToast()

  useEffect(() => {
    const t = setTimeout(() => {
      api('/clients', { params: { q } }).then(setList).catch((e) => toast(e.message, 'err'))
    }, 250)
    return () => clearTimeout(t)
  }, [q])

  const reload = () => api('/clients', { params: { q } }).then(setList).catch(() => {})

  return (
    <div>
      <div className="flex-between mb">
        <h2 className="page-title" style={{ margin: 0 }}>Клиенты</h2>
        <button className="btn" onClick={() => setSel({ isNew: true })}>＋ Клиент</button>
      </div>
      <div className="search-bar">
        <input className="input" placeholder="Быстрый поиск по имени или телефону…" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <div className="card" style={{ padding: 8 }}>
        {list === null ? <PageLoading /> : list.length === 0 ? (
          <Empty>Клиентов пока нет. Добавьте первого — или они появятся сами из онлайн-записи 🌐</Empty>
        ) : list.map((c) => (
          <div key={c.id} className="list-item" onClick={() => setSel({ id: c.id })}>
            <div>
              <b>{c.name}</b>
              <div className="sub">{fmtPhone(c.phone)}{c.notes ? ' · ' + c.notes.slice(0, 40) + (c.notes.length > 40 ? '…' : '') : ''}</div>
            </div>
            <span className="muted">›</span>
          </div>
        ))}
      </div>
      {sel && (
        <ClientModal
          clientId={sel.id}
          onClose={() => setSel(null)}
          onChanged={reload}
        />
      )}
    </div>
  )
}
