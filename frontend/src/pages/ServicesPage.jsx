import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Empty, Field, Modal, PageLoading, useToast } from '../ui.jsx'
import { durationLabel, money } from '../utils.js'

function ServiceModal({ service, onClose, onSaved }) {
  const editing = !!service
  const toast = useToast()
  const [form, setForm] = useState(service || { name: '', duration_min: 60, price: 1500, color: '#d6336c', is_active: true })
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  const save = async () => {
    setBusy(true)
    try {
      const body = { ...form, duration_min: Number(form.duration_min), price: Number(form.price) }
      if (editing) await api(`/services/${service.id}`, { method: 'PATCH', body })
      else await api('/services', { method: 'POST', body })
      toast(editing ? 'Услуга обновлена' : 'Услуга добавлена')
      onSaved()
    } catch (e) { toast(e.message, 'err') } finally { setBusy(false) }
  }

  return (
    <Modal title={editing ? 'Услуга' : 'Новая услуга'} onClose={onClose}>
      <Field label="Название">
        <input className="input" value={form.name} onChange={set('name')} autoFocus />
      </Field>
      <div className="row">
        <Field label="Длительность, мин">
          <input className="input" type="number" min="5" step="5" value={form.duration_min} onChange={set('duration_min')} />
        </Field>
        <Field label="Цена, ₽">
          <input className="input" type="number" min="0" value={form.price} onChange={set('price')} />
        </Field>
        <Field label="Цвет">
          <input className="input" type="color" value={form.color} onChange={set('color')} style={{ padding: 4, height: 42 }} />
        </Field>
      </div>
      <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontWeight: 600, fontSize: 14 }}>
        <input type="checkbox" checked={form.is_active} onChange={set('is_active')} />
        Активна (доступна для записи, в т.ч. онлайн)
      </label>
      <div className="flex-between mt">
        <span className="small muted">Окончание записи считается автоматически: начало + {durationLabel(Number(form.duration_min) || 0)}</span>
        <button className="btn" disabled={busy || !form.name.trim()} onClick={save}>Сохранить</button>
      </div>
    </Modal>
  )
}

export default function ServicesPage() {
  const [list, setList] = useState(null)
  const [sel, setSel] = useState(null)
  const toast = useToast()

  const load = () => api('/services').then(setList).catch((e) => toast(e.message, 'err'))
  useEffect(() => { load() }, [])

  const remove = async (s) => {
    if (!confirm(`Удалить услугу «${s.name}»?`)) return
    try {
      await api(`/services/${s.id}`, { method: 'DELETE' })
      toast('Услуга удалена')
      load()
    } catch (e) { toast(e.message, 'err') }
  }

  return (
    <div>
      <div className="flex-between mb">
        <h2 className="page-title" style={{ margin: 0 }}>Услуги</h2>
        <button className="btn" onClick={() => setSel({})}>＋ Услуга</button>
      </div>
      <div className="card" style={{ padding: 8 }}>
        {list === null ? <PageLoading /> : list.length === 0 ? <Empty>Добавьте услуги — от их длительности зависит сетка календаря</Empty> : (
          <table className="table">
            <thead>
              <tr><th></th><th>Название</th><th>Длительность</th><th>Цена</th><th>Статус</th><th></th></tr>
            </thead>
            <tbody>
              {list.map((s) => (
                <tr key={s.id}>
                  <td style={{ width: 20 }}><span className="dot" style={{ background: s.color, width: 12, height: 12, borderRadius: 4, display: 'inline-block' }} /></td>
                  <td><b>{s.name}</b></td>
                  <td>{durationLabel(s.duration_min)}</td>
                  <td>{money(s.price)}</td>
                  <td>{s.is_active ? <span className="badge st-completed">Активна</span> : <span className="badge st-cancelled">Скрыта</span>}</td>
                  <td style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
                    <button className="btn sm secondary" onClick={() => setSel({ service: s })}>Изменить</button>{' '}
                    <button className="btn sm danger" onClick={() => remove(s)}>✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {sel && (
        <ServiceModal
          service={sel.service}
          onClose={() => setSel(null)}
          onSaved={() => { setSel(null); load() }}
        />
      )}
    </div>
  )
}
