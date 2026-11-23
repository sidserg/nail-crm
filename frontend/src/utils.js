export const pad = (n) => String(n).padStart(2, '0')
export const fmtDate = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
export const parseDate = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d) }
export const todayStr = () => fmtDate(new Date())
export const addDays = (s, n) => { const d = parseDate(s); d.setDate(d.getDate() + n); return fmtDate(d) }

export const minToHHMM = (m) => `${pad(Math.floor(m / 60))}:${pad(m % 60)}`
export const hhmmToMin = (s) => { const [h, m] = s.split(':').map(Number); return h * 60 + m }
export const dtToMin = (iso) => hhmmToMin(iso.slice(11, 16))
export const dtToDate = (iso) => iso.slice(0, 10)
export const makeDT = (dateStr, min) => `${dateStr}T${minToHHMM(min)}`
export const nowMin = () => { const d = new Date(); return d.getHours() * 60 + d.getMinutes() }

export const money = (n) => (n ?? 0).toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' ₽'

export const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
export const WEEKDAYS_FULL = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
export const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
export const MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

// Monday=0 … Sunday=6 (matches backend)
export const weekdayIdx = (dateStr) => (parseDate(dateStr).getDay() + 6) % 7

export function ruDate(dateStr, { short = false, withYear = false } = {}) {
  const d = parseDate(dateStr)
  const base = `${d.getDate()} ${short ? MONTHS_SHORT[d.getMonth()] : MONTHS[d.getMonth()]}`
  return withYear ? `${base} ${d.getFullYear()}` : base
}

export function ruDateTime(iso) {
  return `${ruDate(iso.slice(0, 10), { short: true })}, ${iso.slice(11, 16)}`
}

export function fmtPhone(digits) {
  if (!digits) return ''
  if (digits.length === 11 && digits[0] === '7') {
    return `+7 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7, 9)}-${digits.slice(9, 11)}`
  }
  return '+' + digits
}

export const STATUS = {
  confirmed: { label: 'Подтверждена', cls: 'st-confirmed' },
  completed: { label: 'Выполнена', cls: 'st-completed' },
  cancelled: { label: 'Отменена', cls: 'st-cancelled' },
  no_show: { label: 'Неявка', cls: 'st-no_show' },
}

export function durationLabel(min) {
  const h = Math.floor(min / 60), m = min % 60
  if (h && m) return `${h} ч ${m} мин`
  if (h) return `${h} ч`
  return `${m} мин`
}
