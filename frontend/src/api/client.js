// Thin fetch wrapper. All requests go through the /api proxy (see
// vite.config.js) so the browser always talks to same-origin /api/*.

const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Request failed (${res.status}): ${text}`)
  }
  return res.json()
}

export const api = {
  health: () => request('/health'),
  listModels: () => request('/ev-models/'),
  calculateTco: (payload) =>
    request('/tco/calculate', { method: 'POST', body: JSON.stringify(payload) }),
  estimateSoh: (payload) =>
    request('/soh/estimate', { method: 'POST', body: JSON.stringify(payload) }),
  askPolicy: (payload) =>
    request('/policy/ask', { method: 'POST', body: JSON.stringify(payload) }),
  recommend: (payload) =>
    request('/recommend/', { method: 'POST', body: JSON.stringify(payload) }),
}
