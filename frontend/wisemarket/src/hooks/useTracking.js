// ============================================================
// WISEMARKET — BEHAVIOUR TRACKING
// Stores user interactions locally
// Foundation for smart recommendations
// ============================================================

const MAX_HISTORY = 200

function getHistory() {
  try {
    return JSON.parse(localStorage.getItem('wm_history') || '[]')
  } catch { return [] }
}

function saveHistory(history) {
  localStorage.setItem('wm_history', JSON.stringify(history.slice(-MAX_HISTORY)))
}

export function track(event, data = {}) {
  const history = getHistory()
  history.push({
    event,                          // search | scan | view | add | buy
    ...data,                        // gtin, name, category, store, price
    hour:    new Date().getHours(),
    day:     new Date().getDay(),
    month:   new Date().getMonth() + 1,
    ts:      Date.now(),
  })
  saveHistory(history)
}

// Get smart suggestions based on behaviour
export function getSmartSuggestions() {
  const history = getHistory()
  if (history.length < 3) return []

  // Count searches
  const searches = history
    .filter(h => h.event === 'search' && h.query)
    .map(h => h.query.toLowerCase())

  const counts = {}
  searches.forEach(s => { counts[s] = (counts[s] || 0) + 1 })

  // Return top searched terms
  return Object.entries(counts)
    .sort(([,a],[,b]) => b - a)
    .slice(0, 5)
    .map(([term]) => term)
}

// Get frequently bought products
export function getFrequentProducts() {
  const history = getHistory()
  const adds = history.filter(h => h.event === 'add' && h.gtin)
  const counts = {}
  adds.forEach(h => {
    const key = h.gtin
    counts[key] = { count: (counts[key]?.count || 0) + 1, name: h.name, gtin: h.gtin }
  })
  return Object.values(counts).sort((a,b) => b.count - a.count).slice(0, 5)
}

// Get preferred store
export function getPreferredStore() {
  const history = getHistory()
  const stores = history.filter(h => h.store).map(h => h.store)
  const counts = {}
  stores.forEach(s => { counts[s] = (counts[s] || 0) + 1 })
  return Object.entries(counts).sort(([,a],[,b]) => b-a)[0]?.[0] || null
}

export function useTracking() {
  return { track, getSmartSuggestions, getFrequentProducts, getPreferredStore }
}
