import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { Empty, PageLoading, useToast } from '../ui.jsx'
import { pad, WEEKDAYS } from '../utils.js'

const MONTHS_NOM = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
]

function heatLevel(count) {
  if (count <= 0) return 0
  if (count >= 5) return 5
  return count
}

export default function OverviewPage() {
  const navigate = useNavigate()
  const toast = useToast()

  const [cursor, setCursor] = useState(() => {
    const now = new Date()
    return { year: now.getFullYear(), month: now.getMonth() + 1 }
  })
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const { year, month } = cursor

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)

    api('/overview/stats', { params: { year, month } })
      .then((data) => {
        if (!alive) return
        setStats(data)
        setLoading(false)
      })
      .catch((e) => {
        if (!alive) return
        setError(e.message)
        setLoading(false)
        toast(e.message, 'err')
      })

    return () => { alive = false }
  }, [year, month, toast])

  const shiftMonth = (delta) => {
    setCursor((c) => {
      const d = new Date(c.year, c.month - 1 + delta, 1)
      return { year: d.getFullYear(), month: d.getMonth() + 1 }
    })
  }

  const cells = useMemo(() => {
    const firstWeekday = (new Date(year, month - 1, 1).getDay() + 6) % 7
    const daysInMonth = new Date(year, month, 0).getDate()

    const list = [
      ...Array.from({ length: firstWeekday }, () => null),
      ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
    ]
    while (list.length % 7 !== 0) list.push(null)
    return list
  }, [year, month])

  const total = stats
    ? Object.values(stats).reduce((sum, n) => sum + Number(n || 0), 0)
    : 0

  const openDay = (day) => {
    const count = Number(stats?.[String(day)] || 0)
    if (count <= 0) return
    navigate(`/?date=${year}-${pad(month)}-${pad(day)}`)
  }

  const title = `${MONTHS_NOM[month - 1]} ${year}`

  return (
    <div>
      <div className="flex-between mb">
        <h2 className="page-title" style={{ margin: 0 }}>Обзор</h2>
        <div className="overview-month">
          <button className="icon-btn" onClick={() => shiftMonth(-1)} aria-label="Предыдущий месяц">‹</button>
          <div className="overview-month-title">{title}</div>
          <button className="icon-btn" onClick={() => shiftMonth(1)} aria-label="Следующий месяц">›</button>
        </div>
      </div>

      <div className="card">
        {loading ? <PageLoading /> : error ? <Empty>{error}</Empty> : (
          <>
            <div className="overview-grid overview-weekdays">
              {WEEKDAYS.map((wd) => (
                <div key={wd} className="overview-weekday">{wd}</div>
              ))}
            </div>

            <div className="overview-grid">
              {cells.map((day, idx) => {
                if (day === null) {
                  return <div key={`empty-${idx}`} className="overview-cell empty" aria-hidden="true" />
                }

                const count = Number(stats?.[String(day)] || 0)
                const level = heatLevel(count)
                const clickable = count > 0

                return (
                  <button
                    key={day}
                    type="button"
                    className={`overview-cell heat-${level}` + (clickable ? ' clickable' : '')}
                    disabled={!clickable}
                    onClick={() => openDay(day)}
                    title={clickable ? `Записей: ${count}. Открыть календарь` : 'Нет записей'}
                  >
                    <span className="day-num">{day}</span>
                    {clickable && <span className="day-count">{count}</span>}
                  </button>
                )
              })}
            </div>

            <div className="overview-legend">
              <span><i className="overview-swatch heat-0" />0</span>
              <span><i className="overview-swatch heat-1" />1</span>
              <span><i className="overview-swatch heat-2" />2</span>
              <span><i className="overview-swatch heat-3" />3</span>
              <span><i className="overview-swatch heat-4" />4</span>
              <span><i className="overview-swatch heat-5" />5+</span>
            </div>

            <div className="small muted mt">
              Активных записей за месяц: <b>{total}</b>. Кликните по дню с записями, чтобы открыть календарь на эту дату.
            </div>
          </>
        )}
      </div>
    </div>
  )
}
