import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api.js'
import { useSettings } from '../App.jsx'
import { Field, Modal, PageLoading, useToast } from '../ui.jsx'
import {
  addDays, dtToDate, dtToMin, durationLabel, fmtPhone, hhmmToMin, makeDT,
  minToHHMM, money, nowMin, ruDate, STATUS, todayStr, WEEKDAYS_FULL, weekdayIdx,
} from '../utils.js'

const ROW = 48

/* ================= Day grid ================= */
function DayGrid({ settings, appts, dateStr, showCancelled, onSlot, onAppt }) {
  const startMin = hhmmToMin(settings.work_start)
  const endMin = hhmmToMin(settings.work_end)
  const step = Number(settings.slot_step)
  const rows = Math.max(1, Math.ceil((endMin - startMin) / step))
  const [now, setNow] = useState(nowMin())
  useEffect(() => {
    const t = setInterval(() => setNow(nowMin()), 30000)
    return () => clearInterval(t)
  }, [])

  const visible = appts.filter((a) => showCancelled || a.status !== 'cancelled')
  const isToday = dateStr === todayStr()

  return (
    <div className="grid" style={{ height: rows * ROW }}>
      {Array.from({ length: rows }).map((_, i) => {
        const m = startMin + i * step
        return (
          <div
            key={i}
            className={'grid-row' + (m % 60 !== 0 ? ' half' : '')}
            style={{ top: i * ROW, height: ROW }}
            title={`Записать на ${minToHHMM(m)}`}
            onClick={() => onSlot(m)}
          >
            <span className="grid-time">{minToHHMM(m)}</span>
          </div>
        )
      })}
      {visible.map((a) => {
        const s = dtToMin(a.start_at)
        const e = dtToMin(a.end_at)
        const top = Math.max(0, ((s - startMin) / step) * ROW)
        const h = Math.max(24, ((e - s) / step) * ROW - 4)
        const compact = h <= 48
        return (
          <div
            key={a.id}
            className={`appt ${STATUS[a.status].cls}` + (compact ? ' compact' : '')}
            style={{ top: top + 2, height: h }}
            onClick={(ev) => { ev.stopPropagation(); onAppt(a) }}
          >
            <span className="t">{minToHHMM(s)}–{minToHHMM(e)}</span>
            <span className="n">{a.client.name}</span>
            <span className="s">
              {a.service.name}
              {a.source === 'online' ? ' · 🌐' : ''}
              {a.client_confirmed ? ' · ✅' : ''}
            </span>
            <span className="price-tag">{money(a.price)}</span>
          </div>
        )
      })}
      {isToday && now >= startMin && now <= endMin && (
        <div className="now-line" style={{ top: ((now - startMin) / step) * ROW }} />
      )}
    </div>
  )
}

/* ================= Client picker ================= */
function ClientPicker({ value, onChange }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const toast = useToast()

  useEffect(() => {
    if (!open) return
    const t = setTimeout(() => {
      api('/clients', { params: { q } }).then(setResults).catch(() => {})
    }, 250)
    return () => clearTimeout(t)
  }, [q, open])

  const createClient = async () => {
    try {
      const c = await api('/clients', { method: 'POST', body: { name, phone } })
      onChange(c)
      setCreating(false)
      toast('Клиент создан')
    } catch (e) { toast(e.message, 'err') }
  }

  if (value) {
    return (
      <div className="selected-chip">
        <div>
          {value.name}
          <div className="sub">{fmtPhone(value.phone)}</div>
        </div>
        <button type="button" className="btn sm secondary" onClick={() => { onChange(null); setQ(''); setOpen(true) }}>
          Изменить
        </button>
      </div>
    )
  }

  return (
    <div>
      <div className="picker">
        <input
          className="input"
          placeholder="Поиск: имя или телефон…"
          value={q}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 200)}
          onChange={(e) => { setQ(e.target.value); setOpen(true) }}
        />
        {open && (
          <div className="picker-drop">
            {results.map((c) => (
              <div key={c.id} className="picker-item" onMouseDown={() => { onChange(c); setOpen(false) }}>
                {c.name}
                <div className="sub">{fmtPhone(c.phone)}</div>
              </div>
            ))}
            {results.length === 0 && <div className="picker-item muted">Никого не найдено</div>}
            {q.trim() && (
              <div
                className="picker-item create"
                onMouseDown={() => {
                  setCreating(true); setOpen(false)
                  const digits = q.replace(/\D/g, '')
                  setPhone(digits.length >= 6 ? q.trim() : '')
                  setName(digits.length >= 6 ? '' : q.trim())
                }}
              >
                ＋ Создать клиента «{q.trim()}»
              </div>
            )}
          </div>
        )}
      </div>
      {creating && (
        <div className="card mt">
          <Field label="Имя">
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </Field>
          <Field label="Телефон">
            <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+7 …" inputMode="tel" />
          </Field>
          <div className="row">
            <button type="button" className="btn" disabled={!name.trim() || !phone.trim()} onClick={createClient}>Создать</button>
            <button type="button" className="btn ghost" onClick={() => setCreating(false)}>Отмена</button>
          </div>
        </div>
      )}
    </div>
  )
}

/* ================= Booking modal ================= */
function BookingModal({ dateStr, startMin, appt, presetClientId, onClose, onSaved }) {
  const editing = !!appt
  const toast = useToast()
  const [services, setServices] = useState([])
  const [clientObj, setClientObj] = useState(editing ? appt.client : null)
  const [serviceId, setServiceId] = useState(editing ? appt.service_id : null)
  const [dateLocal, setDateLocal] = useState(editing ? dtToDate(appt.start_at) : dateStr)
  const [timeMin, setTimeMin] = useState(editing ? dtToMin(appt.start_at) : (startMin ?? null))
  const [price, setPrice] = useState(editing ? String(appt.price ?? '') : '')
  const [comment, setComment] = useState(editing ? appt.comment : '')
  const [status, setStatus] = useState(editing ? appt.status : 'confirmed')
  const [slots, setSlots] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api('/services').then((list) => {
      setServices(list)
      if (!editing) {
        const first = list.find((s) => s.is_active) || list[0]
        if (first) { setServiceId(first.id); setPrice(String(first.price)) }
      }
    }).catch((e) => toast(e.message, 'err'))
    if (presetClientId) {
      api(`/clients/${presetClientId}`).then((d) => setClientObj(d.client)).catch(() => {})
    }
  }, [])

  useEffect(() => {
    if (!serviceId) return
    setSlots(null)
    api('/slots', { params: { date: dateLocal, service_id: serviceId } })
      .then(setSlots)
      .catch((e) => toast(e.message, 'err'))
  }, [serviceId, dateLocal])

  const freeOptions = useMemo(() => {
    if (!slots) return []
    const opts = slots.filter((s) => s.available).map((s) => dtToMin(s.start))
    if (editing && dateLocal === dtToDate(appt.start_at)) {
      const orig = dtToMin(appt.start_at)
      if (!opts.includes(orig)) opts.push(orig)
    }
    return opts.sort((a, b) => a - b)
  }, [slots, dateLocal, editing, appt])

  useEffect(() => {
    if (!slots) return
    if (timeMin == null || !freeOptions.includes(timeMin)) {
      setTimeMin(freeOptions[0] ?? null)
    }
  }, [slots])

  const service = services.find((s) => s.id === Number(serviceId))

  const changeService = (id) => {
    setServiceId(Number(id))
    const s = services.find((x) => x.id === Number(id))
    if (s) setPrice(String(s.price))
  }

  const save = async () => {
    setBusy(true)
    try {
      const body = {
        client_id: clientObj.id,
        service_id: Number(serviceId),
        start_at: makeDT(dateLocal, timeMin),
        price: price === '' ? null : Number(price),
        comment,
      }
      if (editing) {
        await api(`/appointments/${appt.id}`, { method: 'PATCH', body: { ...body, status } })
      } else {
        await api('/appointments', { method: 'POST', body })
      }
      toast(editing ? 'Запись обновлена' : 'Клиент записан ✅')
      onSaved()
    } catch (e) {
      toast(e.message, 'err')
      if (e.status === 409 && serviceId) {
        api('/slots', { params: { date: dateLocal, service_id: serviceId } }).then(setSlots).catch(() => {})
      }
    } finally { setBusy(false) }
  }

  const remove = async () => {
    if (!confirm('Удалить эту запись?')) return
    try {
      await api(`/appointments/${appt.id}`, { method: 'DELETE' })
      toast('Запись удалена')
      onSaved()
    } catch (e) { toast(e.message, 'err') }
  }

  return (
    <Modal title={editing ? 'Запись' : 'Новая запись'} onClose={onClose}>
      <Field label="Клиент">
        <ClientPicker value={clientObj} onChange={setClientObj} />
      </Field>
      <Field label="Услуга">
        <select className="input" value={serviceId ?? ''} onChange={(e) => changeService(e.target.value)}>
          {services.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} · {durationLabel(s.duration_min)} · {money(s.price)}{!s.is_active ? ' (скрыта)' : ''}
            </option>
          ))}
        </select>
      </Field>
      <div className="row">
        <Field label="Дата">
          <input className="input" type="date" value={dateLocal} onChange={(e) => e.target.value && setDateLocal(e.target.value)} />
        </Field>
        <Field label="Начало">
          <select className="input" value={timeMin ?? ''} onChange={(e) => setTimeMin(Number(e.target.value))}>
            {slots === null && <option value="">…</option>}
            {slots !== null && freeOptions.length === 0 && <option value="">Нет свободных окон</option>}
            {freeOptions.map((m) => <option key={m} value={m}>{minToHHMM(m)}</option>)}
          </select>
        </Field>
      </div>
      {service && timeMin != null && (
        <div className="small muted mb">
          Окончание: <b>{minToHHMM(timeMin + service.duration_min)}</b> · длительность {durationLabel(service.duration_min)} — время подобрано без накладок
        </div>
      )}
      <div className="row">
        <Field label="Цена, ₽">
          <input className="input" type="number" min="0" value={price} onChange={(e) => setPrice(e.target.value)} />
        </Field>
        {editing && (
          <Field label="Статус">
            <div className="status-btns">
              {Object.entries(STATUS).map(([k, v]) => (
                <button key={k} type="button" className={`${v.cls}` + (status === k ? ' active' : '')} onClick={() => setStatus(k)}>
                  {v.label}
                </button>
              ))}
            </div>
          </Field>
        )}
      </div>
      <Field label="Комментарий">
        <textarea className="input" value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Дизайн, пожелания…" />
      </Field>
      <div className="flex-between mt">
        {editing ? <button className="btn danger" onClick={remove}>Удалить</button> : <span />}
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn ghost" onClick={onClose}>Отмена</button>
          <button className="btn" disabled={busy || !clientObj || !serviceId || timeMin == null} onClick={save}>
            {editing ? 'Сохранить' : 'Записать'}
          </button>
        </div>
      </div>
    </Modal>
  )
}

/* ================= Page ================= */
export default function CalendarPage() {
  const { settings } = useSettings()
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const dateParam = params.get('date')
  const [dateStr, setDateStr] = useState(() =>
    dateParam && /^\d{4}-\d{2}-\d{2}$/.test(dateParam) ? dateParam : todayStr()
  )
  const [appts, setAppts] = useState(null)
  const [showCancelled, setShowCancelled] = useState(false)
  const [modal, setModal] = useState(null)

  const load = useCallback(() => {
    api('/appointments', { params: { from: dateStr, to: dateStr } })
      .then(setAppts)
      .catch((e) => toast(e.message, 'err'))
  }, [dateStr])

  useEffect(() => { setAppts(null); load() }, [load])

  // Support navigation from Overview: /?date=YYYY-MM-DD
  useEffect(() => {
    if (dateParam && /^\d{4}-\d{2}-\d{2}$/.test(dateParam)) setDateStr(dateParam)
  }, [dateParam])

  useEffect(() => {
    const cid = params.get('client')
    if (cid) {
      setModal({ presetClientId: Number(cid), startMin: null })
      const next = new URLSearchParams(params)
      next.delete('client')
      setParams(next, { replace: true })
    }
  }, [params, setParams])

  const active = (appts || []).filter((a) => a.status === 'confirmed' || a.status === 'completed')
  const done = (appts || []).filter((a) => a.status === 'completed')
  const planned = active.reduce((s, a) => s + (a.price || 0), 0)
  const doneSum = done.reduce((s, a) => s + (a.price || 0), 0)

  return (
    <div>
      <div className="cal-head">
        <div className="cal-title">
          {ruDate(dateStr, { withYear: true })}
          <span className="wd">{WEEKDAYS_FULL[weekdayIdx(dateStr)]}{dateStr === todayStr() ? ' · сегодня' : ''}</span>
        </div>
        <button className="icon-btn" onClick={() => setDateStr(addDays(dateStr, -1))} aria-label="Предыдущий день">‹</button>
        <input className="input" style={{ width: 'auto' }} type="date" value={dateStr} onChange={(e) => e.target.value && setDateStr(e.target.value)} />
        <button className="icon-btn" onClick={() => setDateStr(addDays(dateStr, 1))} aria-label="Следующий день">›</button>
        <button className="btn sm secondary" onClick={() => setDateStr(todayStr())}>Сегодня</button>
        <button className="btn sm" onClick={() => setModal({ startMin: null })}>＋ Запись</button>
      </div>

      <div className="cal-summary">
        <span className="sum-chip">Записей: <b>{active.length}</b></span>
        <span className="sum-chip">План: <b>{money(planned)}</b></span>
        <span className="sum-chip">Выполнено: <b>{money(doneSum)}</b></span>
        {active.length > 0 && <span className="sum-chip">Загрузка: <b>{Math.round(active.reduce((s, a) => s + (dtToMin(a.end_at) - dtToMin(a.start_at)), 0) / (hhmmToMin(settings.work_end) - hhmmToMin(settings.work_start)) * 100)}%</b></span>}
      </div>

      {appts === null ? <PageLoading /> : (
        <DayGrid
          settings={settings}
          appts={appts}
          dateStr={dateStr}
          showCancelled={showCancelled}
          onSlot={(m) => setModal({ startMin: m })}
          onAppt={(a) => setModal({ appt: a })}
        />
      )}

      <div className="legend">
        <span><span className="dot" style={{ background: 'var(--rose)' }} />Подтверждена</span>
        <span><span className="dot" style={{ background: 'var(--green)' }} />Выполнена</span>
        <span><span className="dot" style={{ background: 'var(--amber)' }} />Неявка</span>
        <span>🌐 онлайн-запись</span>
        <label>
          <input type="checkbox" checked={showCancelled} onChange={(e) => setShowCancelled(e.target.checked)} />
          показывать отменённые
        </label>
      </div>

      {modal && (
        <BookingModal
          dateStr={dateStr}
          startMin={modal.startMin}
          appt={modal.appt}
          presetClientId={modal.presetClientId}
          onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load() }}
        />
      )}
    </div>
  )
}
