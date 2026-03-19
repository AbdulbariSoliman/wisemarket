import { useState } from 'react'
import { Trash2, Plus, Minus, Download, ShoppingBag } from 'lucide-react'
import { api } from '../api/client'

export default function Basket() {
  const [items, setItems]         = useState([])
  const [totals, setTotals]       = useState(null)
  const [loading, setLoading]     = useState(false)
  const [exporting, setExporting] = useState(false)
  const [gtin, setGtin]           = useState('')
  const lang = localStorage.getItem('lang') || 'en'

  const addItem = () => {
    if (!gtin.trim()) return
    setItems(prev => {
      const ex = prev.find(i => i.gtin === gtin)
      if (ex) return prev.map(i => i.gtin === gtin ? {...i, quantity: i.quantity + 1} : i)
      return [...prev, { gtin: gtin.trim(), quantity: 1 }]
    })
    setGtin('')
    setTotals(null)
  }

  const update = (gtin, delta) => {
    setItems(prev => prev
      .map(i => i.gtin === gtin ? {...i, quantity: Math.max(0, i.quantity + delta)} : i)
      .filter(i => i.quantity > 0)
    )
    setTotals(null)
  }

  const calculate = async () => {
    if (!items.length) return
    setLoading(true)
    try {
      const data = await api.calculate({ items, lang })
      setTotals(data)
    } catch(e) { console.error(e) }
    finally { setLoading(false) }
  }

  const exportPDF = async () => {
    if (!items.length) return
    setExporting(true)
    try {
      await api.exportPDF({ items, lang, qr_url: 'https://wisemarket.ch' })
    } catch(e) { console.error(e) }
    finally { setExporting(false) }
  }

  return (
    <div style={{ padding: '24px 16px 120px' }}>
      <h1 style={{ fontFamily: 'Syne', fontSize: 24, fontWeight: 800, marginBottom: 20 }}>
        🛒 Basket
      </h1>

      {/* Add item */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        <input value={gtin} onChange={e => setGtin(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addItem()}
          placeholder="Enter GTIN to add product"
          style={{ borderRadius: 12 }} />
        <button onClick={addItem} className="btn-ghost"
          style={{ width: 'auto', padding: '0 16px', whiteSpace: 'nowrap' }}>
          Add
        </button>
      </div>

      {/* Items */}
      {items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--muted)' }}>
          <ShoppingBag size={48} style={{ opacity: 0.3, margin: '0 auto 16px' }} />
          <p style={{ fontSize: 16, fontWeight: 600 }}>Your basket is empty</p>
          <p style={{ fontSize: 14, marginTop: 8 }}>Add GTINs or scan products to compare prices</p>
        </div>
      ) : (
        <>
          {items.map((item, i) => (
            <div key={item.gtin} className="card animate-in" style={{
              marginBottom: 10, display: 'flex',
              justifyContent: 'space-between', alignItems: 'center',
              animationDelay: `${i * 0.05}s`,
            }}>
              <div>
                <p style={{ fontFamily: 'Syne', fontWeight: 600, fontSize: 13 }}>
                  {item.gtin}
                </p>
                {totals?.item_breakdown?.find(b => b.gtin === item.gtin)?.name && (
                  <p style={{ color: 'var(--muted)', fontSize: 12, marginTop: 2 }}>
                    {totals.item_breakdown.find(b => b.gtin === item.gtin).name}
                  </p>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <button onClick={() => update(item.gtin, -1)} style={{
                  background: 'var(--border)', border: 'none', borderRadius: 8,
                  width: 28, height: 28, cursor: 'pointer', display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                }}>
                  <Minus size={14} />
                </button>
                <span style={{ fontFamily: 'Syne', fontWeight: 700, minWidth: 20,
                               textAlign: 'center' }}>{item.quantity}</span>
                <button onClick={() => update(item.gtin, 1)} style={{
                  background: 'var(--red)', border: 'none', borderRadius: 8,
                  width: 28, height: 28, cursor: 'pointer', display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                }}>
                  <Plus size={14} color="white" />
                </button>
                <button onClick={() => setItems(prev => prev.filter(i => i.gtin !== item.gtin))}
                  style={{ background: 'none', border: 'none', cursor: 'pointer',
                           color: 'var(--muted)', padding: 4 }}>
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}

          {/* Calculate */}
          <button className="btn-primary" onClick={calculate} disabled={loading}
            style={{ marginBottom: 10 }}>
            {loading ? 'Calculating...' : '💰 Compare Prices'}
          </button>

          {/* Totals */}
          {totals && (
            <div className="card animate-in" style={{ marginBottom: 10 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>
                Store Totals
              </h3>
              {Object.entries(totals.store_totals_chf)
                .sort(([,a],[,b]) => a - b)
                .map(([store, total]) => (
                  <div key={store} style={{
                    display: 'flex', justifyContent: 'space-between',
                    padding: '10px 0', borderBottom: '1px solid var(--border)',
                    alignItems: 'center',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ textTransform: 'capitalize', fontSize: 14,
                                     fontWeight: store === totals.cheapest_complete_store ? 700 : 400 }}>
                        {store}
                      </span>
                      {store === totals.cheapest_complete_store && (
                        <span style={{ background: '#0d3320', color: '#4ade80',
                                       fontSize: 10, padding: '2px 8px',
                                       borderRadius: 10, fontWeight: 600 }}>
                          ★ Cheapest
                        </span>
                      )}
                      {totals.store_missing_items?.[store]?.length > 0 && (
                        <span style={{ color: 'var(--muted)', fontSize: 11 }}>
                          ({totals.store_missing_items[store].length} missing)
                        </span>
                      )}
                    </div>
                    <span style={{
                      fontFamily: 'Syne', fontWeight: 700, fontSize: 16,
                      color: store === totals.cheapest_complete_store ? '#4ade80' : 'var(--text)',
                    }}>
                      CHF {total.toFixed(2)}
                    </span>
                  </div>
                ))}
            </div>
          )}

          {/* Export PDF */}
          <button className="btn-ghost" onClick={exportPDF} disabled={exporting}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <Download size={16} />
            {exporting ? 'Generating PDF...' : 'Export Shopping List PDF'}
          </button>
        </>
      )}
    </div>
  )
}
