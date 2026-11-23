import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api.js'
import { Field, PageLoading, Spinner, useToast } from '../ui.jsx'
import { addDays, durationLabel, money, parseDate, ruDate, ruDateTime, todayStr, WEEKDAYS, weekdayIdx } from '../utils.js'

export default function BookPage() {
  const toast = useToast()
  const [config, setConfig] = useState(null)
  const [services, setServices] = useState([])
  const [serviceId, setServiceId] = useState(null)
  const [dateStr, setDateStr] = useState(null)
  const [slots, setSlots] = useState(null)
  const [slot, setSlot] = useState(null)
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(null)

  useEffect(() => {
    api('/public/config').then(setConfig).catch((e) => toast(e.message, 'err'))
    api('/public/services').then(setServices).catch(() => {})
  }, [])

  const dates = useMemo(() => {
    if (!config) return []
    const workDays = (config.work_days || '').split(',')
    const out = []
    for (let i = 0; i < Math.min(config.booking_horizon_days, 30); i++) {
      const d = addDays(todayStr(), i)
      if (workDays.includes(String(weekdayIdx(d)))) out.push(d)
      if (out.length >= 14) break
    }
    return out
  }, [config])

  useEffect(() => {
    if (!serviceId || !dateStr) return
    setSlots(null); setSlot(null)
    api('/public/slots', { params: { date: dateStr, service_id: serviceId } })
      .then(setSlots)
      .catch((e) => toast(e.message, 'err'))
  }, [serviceId, dateStr])

  const pickService = (id) => {
    setServiceId(id)
    if (!dateStr && dates.length) setDateStr(dates[0])
  }

  const submit = async () => {
    setBusy(true)
    try {
      const res = await api('/public/book', {
        method: 'POST',
        body: { name, phone, service_id: serviceId, start_at: slot, comment },
      })
      setDone(res)
    } catch (e) {
      toast(e.message, 'err')
      if (e.status === 409 && serviceId && dateStr) {
        api('/public/slots', { params: { date: dateStr, service_id: serviceId } }).then(setSlots).catch(() => {})
        setSlot(null)
      }
    } finally { setBusy(false) }
  }

  const reset = () => {
    setDone(null); setServiceId(null); setDateStr(null); setSlots(null); setSlot(null)
    setName(''); setPhone(''); setComment('')
  }

  if (!config) return <div className="book-wrap"><PageLoading /></div>

  const service = services.find((s) => s.id === serviceId)

  return (
    <div className="book-wrap">
      <div className="book-hero">
        <div className="logo">💅</div>
        <h1>{config.salon_name}</h1>
        {config.salon_address && <div className="addr">📍 {config.salon_address}</div>}
        <div className="addr">Онлайн-запись — выберите удобное время</div>
      </div>

      {done ? (
        <div className="book-success">
          <div className="big">🎉</div>
          <h2 style={{ margin: '8px 0' }}>Вы записаны!</h2>
          <p style={{ fontSize: 16 }}>
            <b>{done.appointment.service}</b><br />
            {ruDateTime(done.appointment.start_at)} – {done.appointment.end_at.slice(11, 16)}<br />
            <span className="muted">Стоимость: {money(done.appointment.price)}</span>
          </p>
          {done.salon_address && <p className="muted small">📍 {done.salon_address}</p>}
          <p className="small muted">Мастер уже получил уведомление о вашей записи. Если планы изменятся — пожалуйста, свяжитесь с мастером заранее 🙏</p>
          <button className="btn secondary" onClick={reset}>Записаться ещё</button>
        </div>
      ) : (
        <div>
          <div className="step-title"><span className="step-num">1</span> Услуга</div>
          {services.map((s) => (
            <div key={s.id} className={'svc-card' + (serviceId === s.id ? ' active' : '')} onClick={() => pickService(s.id)}>
              <div>
                <div className="nm">{s.name}</div>
                <div className="dur">{durationLabel(s.duration_min)}</div>
              </div>
              <div className="pr">{money(s.price)}</div>
            </div>
          ))}

          {serviceId && (
            <div>
              <div className="step-title"><span className="step-num">2</span> Дата и время</div>
              <div className="chips">
                {dates.map((d) => (
                  <button key={d} className={'chip' + (dateStr === d ? ' active' : '')} onClick={() => setDateStr(d)}>
                    <span className="wd">{WEEKDAYS[weekdayIdx(d)]}</span>
                    {ruDate(d, { short: true })}
                  </button>
                ))}
              </div>
              <div className="tz-note">Время указано в часовом поясе салона ({config.tz})</div>
              <div className="mt">
                {slots === null ? <Spinner /> : slots.length === 0 ? (
                  <div className="empty">На этот день свободных окон нет — выберите другую дату 🌸</div>
                ) : (
                  <div className="slot-grid">
                    {slots.map((s) => {
                      const t = s.start.slice(11, 16)
                      return (
                        <button key={s.start} className={'slot' + (slot === s.start ? ' active' : '')} onClick={() => setSlot(s.start)}>
                          {t}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {slot && (
            <div>
              <div className="step-title"><span className="step-num">3</span> Контакты</div>
              <div className="card">
                <div className="small mb">
                  {service.name} · <b>{ruDateTime(slot)}</b> · {money(service.price)}
                </div>
                <Field label="Ваше имя">
                  <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Как к вам обращаться?" />
                </Field>
                <Field label="Телефон">
                  <input className="input" type="tel" inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+7 900 000-00-00" />
                </Field>
                <Field label="Комментарий (необязательно)">
                  <textarea className="input" value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Пожелания по дизайну…" rows={2} />
                </Field>
                <button className="btn block" disabled={busy || name.trim().length < 2 || phone.replace(/\D/g, '').length < 10} onClick={submit}>
                  {busy ? 'Записываем…' : 'Записаться ✨'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      <div className="book-footer">Nail CRM · онлайн-запись работает круглосуточно</div>
    </div>
  )
}
