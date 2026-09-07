const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

// Set by AuthContext after login. Kept as a module-level variable (not
// React state) so plain fetch calls in this file can read it without
// needing to be React components themselves.
let authToken = null
export function setAuthToken(token) {
  authToken = token
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      // response wasn't JSON — keep statusText
    }
    throw new Error(detail)
  }
  return res.json()
}

export const ssoLogin = (msTokenId) =>
  request('/auth/sso-login', { method: 'POST', body: JSON.stringify({ token: msTokenId }) })
export const passwordLogin = (email, password) =>
  request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
export const getMe = () => request('/auth/me')

export const listParts = () => request('/parts')
export const getCorrelation = (partCode) => request(`/parts/${partCode}/correlation`)
export const buildRule = (partCode, method, signals) =>
  request(`/parts/${partCode}/rule`, { method: 'POST', body: JSON.stringify({ method, signals }) })
export const getRule = (partCode, method = 'point_biserial') =>
  request(`/parts/${partCode}/rule?method=${method}`)

export const runPredictions = (partCode, method = 'point_biserial') =>
  request('/predictions/run', { method: 'POST', body: JSON.stringify({ part_code: partCode, method }) })
export const listPredictions = (partCode, riskTier, limit) => {
  const params = new URLSearchParams({ part_code: partCode })
  if (riskTier) params.set('risk_tier', riskTier)
  if (limit) params.set('limit', limit)
  return request(`/predictions?${params.toString()}`)
}
export const getPredictionDetail = (vin, partCode, method = 'point_biserial') =>
  request(`/predictions/${vin}/${partCode}?method=${method}`)

export const getRul = (vin, partCode, method = 'point_biserial') =>
  request(`/vins/${vin}/parts/${partCode}/rul?method=${method}`)
export const runRul = (partCode, method = 'point_biserial') =>
  request('/rul/run', { method: 'POST', body: JSON.stringify({ part_code: partCode, method }) })

export const searchVehicles = (q, limit = 8) =>
  request(`/vehicles/search?q=${encodeURIComponent(q)}&limit=${limit}`)

export const getMaintenanceCalendar = () => request('/maintenance/calendar')

export const chatWithAgent = (message, conversationHistory) =>
  request('/agent/chat', { method: 'POST', body: JSON.stringify({ message, conversation_history: conversationHistory }) })
export const draftOutreach = (vin, partCode) =>
  request('/agent/draft-outreach', { method: 'POST', body: JSON.stringify({ vin, part_code: partCode }) })
