// ============================================================
// WISEMARKET — API CLIENT
// All calls go through here
// ============================================================
const BASE = import.meta.env.VITE_API_URL || '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  // Health
  health: () => request('/health'),

  // Agent
  greeting: (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return request(`/agent/greeting?${q}`)
  },
  query: (body) => request('/agent/query', {
    method: 'POST', body: JSON.stringify(body)
  }),

  // Products
  search: (params = {}) => {
    const q = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([,v]) => v !== undefined && v !== null && v !== ''))
    ).toString()
    return request(`/products/search?${q}`)
  },
  product: (gtin, params = {}) => {
    const q = new URLSearchParams(params).toString()
    return request(`/products/${gtin}?${q}`)
  },
  nutrition: (gtin) => request(`/products/${gtin}/nutrition`),

  // Prices
  compare: (gtin) => request(`/prices/compare/${gtin}`),
  history: (gtin, params = {}) => {
    const q = new URLSearchParams(params).toString()
    return request(`/prices/history/${gtin}?${q}`)
  },

  // Promotions
  promotions: (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return request(`/promotions?${q}`)
  },

  // Basket
  calculate: (body) => request('/basket/calculate', {
    method: 'POST', body: JSON.stringify(body)
  }),
  basketNutrition: (body) => request('/basket/nutrition', {
    method: 'POST', body: JSON.stringify(body)
  }),

  exportPDF: async (body) => {
    const res = await fetch(`${BASE}/basket/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error('Export failed')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `wisemarket_list.pdf`
    a.click()
    URL.revokeObjectURL(url)
  },

  // Scan
  scan: (body) => request('/scan', {
    method: 'POST', body: JSON.stringify(body)
  }),
}
