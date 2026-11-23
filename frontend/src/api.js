// Tiny fetch wrapper with JWT auth.
const TOKEN_KEY = 'nailcrm_token'
let memToken = null // fallback when storage is unavailable (sandboxed iframes)

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) || memToken } catch { return memToken }
}
export function setToken(t) {
  memToken = t
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ }
}

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status }
}

export async function api(path, { method = 'GET', body, params } = {}) {
  let url = '/api' + path
  if (params) {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') qs.append(k, v)
    }
    const s = qs.toString()
    if (s) url += '?' + s
  }
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const token = getToken()
  if (token) headers['Authorization'] = 'Bearer ' + token

  const res = await fetch(url, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined })
  let data = null
  try { data = await res.json() } catch { /* no body */ }

  if (res.status === 401 && !path.startsWith('/public') && !path.startsWith('/auth/login')) {
    setToken(null)
    if (!location.pathname.startsWith('/book') && !location.pathname.startsWith('/login')) {
      location.assign('/login')
    }
    throw new ApiError('Сессия истекла — войдите заново', 401)
  }
  if (!res.ok) {
    let msg = data && data.detail
    if (Array.isArray(msg)) msg = msg.map((e) => e.msg).join('; ')
    throw new ApiError(msg || `Ошибка ${res.status}`, res.status)
  }
  return data
}

export async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true } catch { /* fallback */ }
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    return true
  } catch { return false }
}
