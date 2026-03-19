import { useState, useEffect } from 'react'
import { Trash2, Plus, Minus, Download, ShoppingBag } from 'lucide-react'
import { api } from '../api/client'

export default function Basket() {
  const [items, setItems]         = useState([])
  const [totals, setTotals]       = useState(null)
  const [loading, setLoading]     = useState(false)
  const [exporting, setExporting] = useState(false)
  const [gtin, setGtin]           = useState('')
  const lang = localStorage.getItem('lang') || 'en'

  // Load from localStorage on mount
  useEffect(() => {
    const saved = JSON.parse(localStorage.getItem('basket') || '[]')
    setItems(saved)
  }, [])

  // Save to localStorage whenever items change
  useEffect(() => {
    localStorage.setItem('basket', JSON.stringify(items))
    setTotals(null)
  }, [items])

  const addItem = () => {
    if (!gtin.trim()) return
    setItems(prev => {
      const ex = prev.find(i => i.gtin === gtin.trim())
      if (ex) return prev.map(i => i.gtin === gtin.trim()
        ? {...i, quantity: i.quantity + 1} : i)
      return [...prev, { gtin: gtin.trim(), quantity: 1 }]
    })
    setGtin('')
  }

  const update = (g, delta) => {
    setItems(prev => prev
      .map(i => i.gtin === g ? {...i, quantity: Math.max(0, i.quantity + delta)} : i)
      .filter(i => i.quantity > 0)
    )
  }

  const remove = (g) => setItems(prev => prev.filter(i => i.gtin !== g))

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
      <div style={{ display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginBottom: 20 }}>
        <h1 style={{ fontFamily: 'Syne', fontSize: 24, fontWeight: 800 }}>
          🛒 Basket
        </h1>
        {items.length > 0 && (
          <span style={{ background: 'var(--red)', color: 'white',
                         borderRadius: 20, padding: '2px 10px', fontSize: 13,
                         fontWeight: 700 }}>
            {items.reduce((s, i) => s + i.quantity, 0)}
          </span>
        )}
      </div>

      {/* Add item */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        <input value={gtin} onChange={e => setGtin(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addItem()}
          placeholder="Enter GTIN to add product"
          style={{ borderRadius: 12 }} />
        <button onClick={addItem} className="btn-ghost"
          style={{ width: 'auto', padding: '0 16px', whiteSpace: 'nowrap' }}>
          + Add
        </button>
      </div>

      {/* Items */}
      {items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--muted)' }}>
          <ShoppingBag size={48} style={{ opacity: 0.3, margin: '0 auto 16px', display: 'block' }} />
          <p style={{ fontSize: 16, fontWeight: 600 }}>Your basket is empty</p>
          <p style={{ fontSize: 14, marginTop: 8 }}>
            Add GTINs above or tap "Add to Basket" on any product
          </p>
        </div>
      ) : (
        <>
          {items.map((item, i) => {
            const breakdown = totals?.item_breakdown?.find(b => b.gtin === item.gtin)
            return (
              <div key={item.gtin} className="card animate-in" style={{
                marginBottom: 10, display: 'flex',
                justifyContent: 'space-between', alignItems: 'center',
                animationDelay: `${i * 0.05}s`,
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontFamily: 'Syne', fontWeight: 600, fontSize: 13,
                               overflow: 'hidden', textOverflow: 'ellipsis',
                               whiteSpace: 'nowrap' }}>
                    {breakdown?.name || item.name || item.gtin}
                  </p>
                  <p style={{ color: 'var(--muted)', fontSize: 11, marginTop: 2 }}>
                    {item.gtin}
                  </p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                  <button onClick={() => update(item.gtin, -1)} style={{
                    background: 'var(--border)', border: 'none', borderRadius: 8,
                    width: 28, height: 28, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <Minus size={14} />
                  </button>
                  <span style={{ fontFamily: 'Syne', fontWeight: 700,
                                 minWidth: 20, textAlign: 'center' }}>
                    {item.quantity}
                  </span>
                  <button onClick={() => update(item.gtin, 1)} style={{
                    background: 'var(--red)', border: 'none', borderRadius: 8,
                    width: 28, height: 28, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <Plus size={14} color="white" />
                  </button>
                  <button onClick={() => remove(item.gtin)} style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--muted)', padding: 4,
                  }}>
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            )
          })}

          <button className="btn-primary" onClick={calculate}
            disabled={loading} style={{ marginBottom: 10 }}>
            {loading ? 'Calculating...' : '💰 Compare Prices Across Stores'}
          </button>

          {/* Totals */}
          {totals && (
            <div className="card animate-in" style={{ marginBottom: 10 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>
                Store Totals
              </h3>
              {Object.entries(totals.store_totals_chf)
                .filter(([, t]) => t > 0)
                .sort(([,a],[,b]) => a - b)
                .map(([store, total]) => (
                  <div key={store} style={{
                    display: 'flex', justifyContent: 'space-between',
                    padding: '10px 0', borderBottom: '1px solid var(--border)',
                    alignItems: 'center', fontSize: 14,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ textTransform: 'capitalize' }}>{store}</span>
                      {totals.store_missing_items?.[store]?.length > 0 && (
                        <span style={{ color: 'var(--muted)', fontSize: 11 }}>
                          ({totals.store_missing_items[store].length} item{totals.store_missing_items[store].length > 1 ? 's' : ''} missing)
                        </span>
                      )}
                    </div>
                    <span style={{ fontFamily: 'Syne', fontWeight: 700, fontSize: 16 }}>
                      CHF {total.toFixed(2)}
                    </span>
                  </div>
                ))}
            </div>
          )}

          <button className="btn-ghost" onClick={exportPDF}
            disabled={exporting}
            style={{ display: 'flex', alignItems: 'center',
                     justifyContent: 'center', gap: 8 }}>
            <Download size={16} />
            {exporting ? 'Generating...' : 'Export Shopping List PDF'}
          </button>
        </>
      )}
    </div>
  )
}
