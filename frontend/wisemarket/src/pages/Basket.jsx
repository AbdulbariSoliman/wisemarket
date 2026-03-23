import { useState, useEffect, useCallback } from 'react'
import { Trash2, Plus, Minus, Download, ShoppingBag, Search } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useBasket } from '../hooks/useBasket'
import { api } from '../api/client'

const STORE_COLORS = {
  migros: '#E05A00', coop: '#C0001A',
  aldi: '#00539F', lidl: '#0050AA', denner: '#C8102E'
}

const STORES = ['migros', 'coop', 'aldi', 'lidl']

function NutritionBar({ label, value, unit, max, color }) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 9 }}>
      <span style={{ fontSize: 12, color: 'var(--muted)', width: 52, flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, height: 5, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.4s ease' }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', width: 56, textAlign: 'right', flexShrink: 0 }}>
        {Math.round(value * 10) / 10} {unit}
      </span>
    </div>
  )
}

export default function Basket() {
  const navigate = useNavigate()
  const { items, setItems, addProduct: addToBasket, removeProduct, updateQuantity } = useBasket()
  const [mode, setMode]         = useState('mix')
  const [store, setStore]       = useState('migros')
  const [data, setData]         = useState(null)
  const [nutrition, setNutrition] = useState(null)
  const [loading, setLoading]   = useState(false)
  const [exporting, setExporting] = useState(false)
  const [search, setSearch]     = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)
  const lang = localStorage.getItem('lang') || 'en'

  useEffect(() => {
    if (items.length > 0) calculate()
    else { setData(null); setNutrition(null) }
  }, [items])

  // Search products to add
  useEffect(() => {
    if (!search.trim()) { setSearchResults([]); return }
    const t = setTimeout(async () => {
      setSearching(true)
      try {
        const res = await api.search({ q: search, lang, limit: 5 })
        // Deduplicate by GTIN
        const seen = new Set()
        const unique = (res.results || []).filter(p => {
          if (seen.has(p.gtin)) return false
          seen.add(p.gtin); return true
        })
        setSearchResults(unique)
      } catch(e) {} finally { setSearching(false) }
    }, 300)
    return () => clearTimeout(t)
  }, [search])

  const calculate = useCallback(async () => {
    if (!items.length) return
    setLoading(true)
    try {
      const [calcData, nutrData] = await Promise.all([
        api.calculate({ items, lang }),
        api.basketNutrition({ items, lang }).catch(() => null),
      ])
      setData(calcData)
      if (nutrData) setNutrition(nutrData)
    } catch(e) { console.error(e) }
    finally { setLoading(false) }
  }, [items, lang])

  const addProduct = (p) => {
    addToBasket(p)
    setSearch('')
    setSearchResults([])
  }

  const update = (gtin, delta) => updateQuantity(gtin, delta)
  const remove = (gtin) => removeProduct(gtin)

  const exportPDF = async () => {
    setExporting(true)
    try {
      await api.exportPDF({ items, lang, qr_url: 'https://wisemarket.ch' })
    } catch(e) {} finally { setExporting(false) }
  }

  // ── Compute display data ──────────────────────────────────

  const getItemDisplay = () => {
    if (!data) return items.map(i => ({
      gtin: i.gtin, name: i.name || i.gtin,
      quantity: i.quantity, store: null, price: null, lineTotal: null, missing: false
    }))

    return data.item_breakdown.map(item => {
      const prices = item.prices || {}
      let chosenStore, price, lineTotal

      if (mode === 'mix') {
        // Find cheapest available store
        const sorted = Object.entries(prices).sort(([,a],[,b]) => a.price_chf - b.price_chf)
        if (sorted.length > 0) {
          [chosenStore] = sorted[0]
          price = sorted[0][1].price_chf
          lineTotal = sorted[0][1].line_total_chf
        }
      } else {
        // One store mode
        chosenStore = store
        if (prices[store]) {
          price = prices[store].price_chf
          lineTotal = prices[store].line_total_chf
        }
      }

      return {
        gtin: item.gtin,
        name: item.name,
        quantity: item.quantity,
        store: chosenStore || null,
        price,
        lineTotal,
        missing: !lineTotal,
        allPrices: prices,
      }
    })
  }

  const getTotal = (displayItems) => {
    return displayItems.reduce((s, i) => s + (i.lineTotal || 0), 0)
  }

  const getWorstTotal = (displayItems) => {
    return displayItems.reduce((s, i) => {
      if (!i.allPrices) return s
      const prices = Object.values(i.allPrices).map(p => p.line_total_chf)
      return s + (prices.length ? Math.max(...prices) : 0)
    }, 0)
  }

  const displayItems = getItemDisplay()
  const total = getTotal(displayItems)
  const worst = getWorstTotal(displayItems)
  const saved = Math.max(0, worst - total)
  const missingCount = displayItems.filter(i => i.missing).length
  const storesUsed = new Set(displayItems.filter(i => i.store).map(i => i.store))

  return (
    <div style={{ padding: '24px 16px 120px' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginBottom: 20 }}>
        <h1 style={{ fontFamily: 'Syne', fontSize: 24, fontWeight: 800 }}>🛒 Basket</h1>
        {items.length > 0 && (
          <span style={{ background: 'var(--red)', color: 'white',
                         borderRadius: 20, padding: '2px 10px',
                         fontSize: 13, fontWeight: 700 }}>
            {items.reduce((s, i) => s + i.quantity, 0)}
          </span>
        )}
      </div>

      {/* Search to add */}
      <div style={{ position: 'relative', marginBottom: 16 }}>
        <Search size={16} color="var(--muted)" style={{
          position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)'
        }} />
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search products to add..."
          style={{ paddingLeft: 42, borderRadius: 12 }} />

        {/* Search dropdown */}
        {searchResults.length > 0 && (
          <div style={{
            position: 'absolute', top: '110%', left: 0, right: 0,
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 12, zIndex: 50, overflow: 'hidden',
            boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
          }}>
            {searchResults.map(p => (
              <div key={p.gtin} onClick={() => addProduct(p)} style={{
                padding: '12px 16px', cursor: 'pointer',
                borderBottom: '1px solid var(--border)',
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', transition: 'background 0.1s',
              }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--border)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <div>
                  <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>
                    {p.name || p.name_en}
                  </p>
                  <p style={{ margin: 0, fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
                    {p.brand} · {p.category}
                  </p>
                </div>
                <Plus size={16} color="var(--red)" />
              </div>
            ))}
          </div>
        )}
      </div>

      {items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--muted)' }}>
          <ShoppingBag size={48} style={{ opacity: 0.3, margin: '0 auto 16px', display: 'block' }} />
          <p style={{ fontSize: 16, fontWeight: 600 }}>Your basket is empty</p>
          <p style={{ fontSize: 14, marginTop: 8 }}>Search products above or scan a barcode</p>
          <button onClick={() => navigate('/scan')} className="btn-primary"
            style={{ marginTop: 16, width: 'auto', padding: '10px 24px' }}>
            Scan a product
          </button>
        </div>
      ) : (
        <>
          {/* Mode toggle */}
          <div style={{ display: 'flex', marginBottom: 12,
                        border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
            {[['mix', 'Cheapest mix'], ['one', 'One store']].map(([m, label]) => (
              <button key={m} onClick={() => setMode(m)} style={{
                flex: 1, padding: '10px 0', fontSize: 13, border: 'none',
                borderRight: m === 'mix' ? '1px solid var(--border)' : 'none',
                background: mode === m ? 'var(--surface)' : 'var(--dark)',
                color: mode === m ? 'var(--text)' : 'var(--muted)',
                fontWeight: mode === m ? 600 : 400,
                cursor: 'pointer', transition: 'all 0.15s',
              }}>{label}</button>
            ))}
          </div>

          {/* Store selector for one-store mode */}
          {mode === 'one' && (
            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              {STORES.map(s => (
                <button key={s} onClick={() => setStore(s)} style={{
                  flex: 1, padding: '8px 4px', fontSize: 12,
                  borderRadius: 10, cursor: 'pointer', transition: 'all 0.15s',
                  border: `1px solid ${store === s ? STORE_COLORS[s] : 'var(--border)'}`,
                  color: store === s ? STORE_COLORS[s] : 'var(--muted)',
                  background: store === s ? 'var(--surface)' : 'var(--dark)',
                  fontWeight: store === s ? 600 : 400, textTransform: 'capitalize',
                }}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}
            </div>
          )}

          {/* Item list */}
          <div className="card" style={{ padding: 0, marginBottom: 12, overflow: 'hidden' }}>
            {displayItems.map((item, i) => (
              <div key={item.gtin} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '12px 16px',
                borderBottom: i < displayItems.length - 1 ? '1px solid var(--border)' : 'none',
                opacity: item.missing ? 0.4 : 1,
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ margin: 0, fontSize: 13, fontWeight: 600,
                               overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.name}
                    {item.quantity > 1 && (
                      <span style={{ color: 'var(--muted)', fontWeight: 400 }}> ×{item.quantity}</span>
                    )}
                  </p>
                  <p style={{ margin: '2px 0 0', fontSize: 11,
                               color: item.missing ? 'var(--muted)' : (STORE_COLORS[item.store] || 'var(--muted)') }}>
                    {item.missing ? '— not available' : `● ${item.store}`}
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                  <button onClick={() => update(item.gtin, -1)} style={{
                    background: 'var(--border)', border: 'none', borderRadius: 7,
                    width: 26, height: 26, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <Minus size={12} />
                  </button>
                  <span style={{ fontFamily: 'Syne', fontWeight: 700, fontSize: 14,
                                 minWidth: 18, textAlign: 'center' }}>
                    {item.quantity}
                  </span>
                  <button onClick={() => update(item.gtin, 1)} style={{
                    background: 'var(--red)', border: 'none', borderRadius: 7,
                    width: 26, height: 26, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <Plus size={12} color="white" />
                  </button>
                  <button onClick={() => remove(item.gtin)} style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--muted)', padding: '0 2px', marginLeft: 2,
                  }}>
                    <Trash2 size={14} />
                  </button>
                </div>

                <span style={{ fontSize: 13, fontWeight: 700, flexShrink: 0,
                               color: item.missing ? 'var(--muted)' : 'var(--text)',
                               minWidth: 64, textAlign: 'right' }}>
                  {item.lineTotal ? `CHF ${item.lineTotal.toFixed(2)}` : '—'}
                </span>
              </div>
            ))}

            {/* Total row */}
            <div style={{ borderTop: '1px solid var(--border)', padding: '12px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
                    {mode === 'mix' ? 'Total · cheapest mix' : `Total · ${store} only`}
                  </p>
                  <p style={{ margin: '2px 0 0', fontSize: 11, color: 'var(--muted)' }}>
                    {mode === 'mix'
                      ? storesUsed.size > 1 ? `${storesUsed.size} stores needed` : '1 store only'
                      : missingCount > 0 ? `${missingCount} item(s) not available` : 'All items available'
                    }
                  </p>
                </div>
                <span style={{ fontFamily: 'Syne', fontSize: 20, fontWeight: 800 }}>
                  CHF {total.toFixed(2)}
                </span>
              </div>

              {/* Savings row */}
              {saved > 0.01 && (
                <div style={{
                  marginTop: 10, padding: '8px 12px', borderRadius: 10,
                  background: 'rgba(45, 198, 83, 0.12)',
                  border: '1px solid rgba(45, 198, 83, 0.25)',
                }}>
                  <p style={{ margin: 0, fontSize: 12, color: '#4ade80', fontWeight: 600 }}>
                    You saved CHF {saved.toFixed(2)} vs the most expensive option
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Nutrition summary */}
          {nutrition?.total && (
            <div className="card" style={{ marginBottom: 12 }}>
              <p style={{ margin: '0 0 14px', fontSize: 13, fontWeight: 600, color: 'var(--muted)' }}>
                Basket nutrition summary
              </p>
              <NutritionBar label="Calories" value={nutrition.total.kcal}    unit="kcal" max={3000} color="#E05A00" />
              <NutritionBar label="Protein"  value={nutrition.total.protein} unit="g"    max={100}  color="#00539F" />
              <NutritionBar label="Fat"      value={nutrition.total.fat}     unit="g"    max={80}   color="#C0001A" />
              <NutritionBar label="Sugar"    value={nutrition.total.sugar}   unit="g"    max={60}   color="#E09000" />
              <NutritionBar label="Salt"     value={nutrition.total.salt}    unit="g"    max={6}    color="#888888" />
            </div>
          )}

          {/* Actions */}
          <button className="btn-ghost" onClick={exportPDF} disabled={exporting}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <Download size={16} />
            {exporting ? 'Generating...' : 'Export Shopping List PDF'}
          </button>
        </>
      )}
    </div>
  )
}
