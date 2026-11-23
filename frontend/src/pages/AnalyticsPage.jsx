import React, { useEffect, useState } from 'react'
import { api, copyText } from '../api.js'
import { Empty, Field, PageLoading, useToast } from '../ui.jsx'
import { addDays, fmtPhone, money, ruDate, todayStr } from '../utils.js'

function BarChart({ data }) {
  const w = 660, h = 170, padX = 8, top = 10
  const max = Math.max(...data.map((d) => d.revenue), 1)
  const bw = (w - padX * 2) / data.length
  const labelEvery = Math.max(1, Math.ceil(data.length / 12))
  return (
    <svg className="chart" viewBox={`0 0 ${w} ${h + 26}`}>
      {data.map((d, i) => {
        const bh = (d.revenue / max) * h
        return (
          <g key={d.date}>
            <rect className="bar" x={padX + i * bw + 2} y={top + h - bh} width={Math.max(bw - 4, 2)} height={Math.max(bh, d.revenue > 0 ? 3 : 0)} rx="3">
              <title>{`${d.date.slice(8, 10)}.${d.date.slice(5, 7)}: ${money(d.revenue)}`}</title>
            </rect>
            {i % labelEvery === 0 && (
              <text x={padX + i * bw + bw / 2} y={h + top + 16} textAnchor="middle">
                {d.date.slice(8, 10)}.{d.date.slice(5, 7)}
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}

const PRESETS = {
  today: () => [todayStr(), todayStr()],
  week: () => [addDays(todayStr(), -6), todayStr()],
  month: () => [todayStr().slice(0, 8) + '01', todayStr()],
}

export default function AnalyticsPage() {
  const toast = useToast()
  const [period, setPeriod] = useState('month')
  const [from, setFrom] = useState(PRESETS.month()[0])
  const [to, setTo] = useState(todayStr())
  const [data, setData] = useState(null)
  const [expenses, setExpenses] = useState([])
  const [inactive, setInactive] = useState(null)
  const [inactiveDays, setInactiveDays] = useState(60)
  const [expForm, setExpForm] = useState({ date: todayStr(), amount: '', category: 'Материалы', comment: '' })

  const loadFinance = () => {
    api('/analytics/summary', { params: { from, to } }).then(setData).catch((e) => toast(e.message, 'err'))
    api('/expenses', { params: { from, to } }).then(setExpenses).catch(() => {})
  }
  useEffect(() => { setData(null); loadFinance() }, [from, to])
  useEffect(() => {
    api('/analytics/inactive', { params: { days: inactiveDays } }).then(setInactive).catch(() => {})
  }, [inactiveDays])

  const applyPreset = (p) => {
    setPeriod(p)
    const [f, t] = PRESETS[p]()
    setFrom(f); setTo(t)
  }

  const addExpense = async () => {
    try {
      await api('/expenses', { method: 'POST', body: { ...expForm, amount: Number(expForm.amount) } })
      setExpForm({ ...expForm, amount: '', comment: '' })
      toast('Расход добавлен')
      loadFinance()
    } catch (e) { toast(e.message, 'err') }
  }

  const removeExpense = async (id) => {
    if (!confirm('Удалить расход?')) return
    try { await api(`/expenses/${id}`, { method: 'DELETE' }); loadFinance() }
    catch (e) { toast(e.message, 'err') }
  }

  const invite = async (c) => {
    const text = `Здравствуйте, ${c.name}! 💅 Вы были у нас ${ruDate(c.last_visit.slice(0, 10))} — самое время обновить маникюр! Свободные окошки и запись онлайн: ${location.origin}/book`
    ;(await copyText(text)) ? toast('Текст приглашения скопирован') : toast('Не удалось скопировать', 'err')
  }

  const maxSvc = data ? Math.max(...data.top_services.map((s) => s.count), 1) : 1

  return (
    <div>
      <div className="flex-between mb">
        <h2 className="page-title" style={{ margin: 0 }}>Финансы и аналитика</h2>
        <div className="seg">
          <button className={period === 'today' ? 'active' : ''} onClick={() => applyPreset('today')}>Сегодня</button>
          <button className={period === 'week' ? 'active' : ''} onClick={() => applyPreset('week')}>7 дней</button>
          <button className={period === 'month' ? 'active' : ''} onClick={() => applyPreset('month')}>Месяц</button>
        </div>
      </div>
      <div className="row mb" style={{ maxWidth: 420 }}>
        <Field label="С"><input className="input" type="date" value={from} onChange={(e) => { setPeriod('custom'); setFrom(e.target.value) }} /></Field>
        <Field label="По"><input className="input" type="date" value={to} onChange={(e) => { setPeriod('custom'); setTo(e.target.value) }} /></Field>
      </div>

      {data === null ? <PageLoading /> : (
        <div>
          <div className="kpis">
            <div className="kpi accent"><div className="v">{money(data.revenue)}</div><div className="l">Выручка</div></div>
            <div className="kpi"><div className="v">{data.completed_count}</div><div className="l">Выполнено записей</div></div>
            <div className="kpi"><div className="v">{money(data.avg_check)}</div><div className="l">Средний чек</div></div>
            <div className="kpi"><div className="v">{money(data.expenses)}</div><div className="l">Расходы</div></div>
            <div className="kpi accent"><div className="v">{money(data.net_profit)}</div><div className="l">Чистая прибыль</div></div>
          </div>

          <div className="card">
            <h3>Выручка по дням</h3>
            <BarChart data={data.revenue_by_day} />
            <div className="small muted mt">
              Отменено: {data.status_counts.cancelled} · Неявки: {data.status_counts.no_show} · В выручку входят только выполненные записи
            </div>
          </div>

          <div className="card">
            <h3>Топ услуг</h3>
            {data.top_services.length === 0 ? <Empty>Пока нет выполненных записей за период</Empty> : data.top_services.map((s, i) => (
              <div key={s.name} className="top-svc">
                <span style={{ width: 20, fontWeight: 800 }} className="muted">{i + 1}</span>
                <span style={{ minWidth: 170, fontSize: 13.5, fontWeight: 600 }}>{s.name}</span>
                <div className="bar-wrap"><div className="bar-in" style={{ width: `${(s.count / maxSvc) * 100}%` }} /></div>
                <span className="small" style={{ whiteSpace: 'nowrap' }}><b>{s.count}</b> × · {money(s.revenue)}</span>
              </div>
            ))}
          </div>

          <div className="card">
            <h3>Расходы за период</h3>
            <div className="row">
              <Field label="Дата"><input className="input" type="date" value={expForm.date} onChange={(e) => setExpForm({ ...expForm, date: e.target.value })} /></Field>
              <Field label="Сумма, ₽"><input className="input" type="number" min="0" value={expForm.amount} onChange={(e) => setExpForm({ ...expForm, amount: e.target.value })} /></Field>
              <Field label="Категория">
                <select className="input" value={expForm.category} onChange={(e) => setExpForm({ ...expForm, category: e.target.value })}>
                  {['Материалы', 'Аренда', 'Инструменты', 'Реклама', 'Обучение', 'Прочее'].map((c) => <option key={c}>{c}</option>)}
                </select>
              </Field>
            </div>
            <div className="row">
              <Field label="Комментарий"><input className="input" value={expForm.comment} onChange={(e) => setExpForm({ ...expForm, comment: e.target.value })} placeholder="Необязательно" /></Field>
              <div className="shrink" style={{ display: 'flex', alignItems: 'flex-end', marginBottom: 12 }}>
                <button className="btn" disabled={!expForm.amount || Number(expForm.amount) <= 0} onClick={addExpense}>＋ Добавить</button>
              </div>
            </div>
            {expenses.length === 0 ? <div className="small muted">Расходов за период нет</div> : expenses.map((e) => (
              <div key={e.id} className="history-item">
                <div><b>{ruDate(e.date, { short: true })}</b> · {e.category}{e.comment ? <span className="muted"> — {e.comment}</span> : ''}</div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <b>{money(e.amount)}</b>
                  <button className="btn sm danger" onClick={() => removeExpense(e.id)}>✕</button>
                </div>
              </div>
            ))}
          </div>

          <div className="card">
            <div className="flex-between">
              <h3 style={{ margin: 0 }}>Пора обновить маникюр 💌</h3>
              <select className="input" style={{ width: 'auto' }} value={inactiveDays} onChange={(e) => setInactiveDays(Number(e.target.value))}>
                <option value={30}>не были 30+ дней</option>
                <option value={60}>не были 60+ дней</option>
                <option value={90}>не были 90+ дней</option>
              </select>
            </div>
            <div className="small muted mb">Клиенты для рассылки-приглашения. Кнопка копирует готовый текст со ссылкой на онлайн-запись.</div>
            {inactive === null ? <PageLoading /> : inactive.length === 0 ? <Empty>Все клиенты свежие — никто не пропал 🎉</Empty> : (
              <table className="table">
                <thead><tr><th>Клиент</th><th>Последний визит</th><th>Потрачено</th><th></th></tr></thead>
                <tbody>
                  {inactive.map((c) => (
                    <tr key={c.id}>
                      <td><b>{c.name}</b><div className="small muted">{fmtPhone(c.phone)}</div></td>
                      <td>{ruDate(c.last_visit.slice(0, 10), { short: true })} <span className="muted small">({c.days_ago} дн. назад)</span></td>
                      <td>{money(c.total_spent)}</td>
                      <td style={{ textAlign: 'right' }}><button className="btn sm secondary" onClick={() => invite(c)}>💌 Пригласить</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
