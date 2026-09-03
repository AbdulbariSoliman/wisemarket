import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mic, ScanLine, Send, X } from 'lucide-react'
import { api } from '../api/client'
import { useBasket } from '../hooks/useBasket'
import { getSeasonalContext, getGreeting } from '../data/seasonal'
import { track } from '../hooks/useTracking'

const STORE_COLORS = { migros:'#E05A00', coop:'#C0001A', aldi:'#00539F', lidl:'#0050AA' }

const DINNERS = [
  { icon:'🐔', name:'Roast Chicken',    search:'poulet kartoffeln kräuter' },
  { icon:'🍝', name:'Pasta Bolognese',  search:'hackfleisch pasta tomaten' },
  { icon:'🥗', name:'Light Salad',      search:'salat lachs avocado' },
  { icon:'🐟', name:'Salmon & Veg',     search:'lachs gemüse zitrone' },
  { icon:'🧀', name:'Raclette Evening', search:'raclettekäse kartoffeln cornichons' },
  { icon:'🍲', name:'Fondue Night',     search:'fonduekäse brot weisswein' },
  { icon:'🍕', name:'Pizza Night',      search:'mozzarella tomaten pizza teig' },
]

export default function Home() {
  const navigate = useNavigate()
  const { addProduct } = useBasket()
  const lang = localStorage.getItem('lang') || 'en'
  const inputRef = useRef()

  const [query, setQuery]       = useState('')
  const [results, setResults]   = useState([])
  const [promotions, setPromotions] = useState([])
  const [loading, setLoading]   = useState(false)
  const [focused, setFocused]   = useState(false)
  const [listening, setListening] = useState(false)

  const seasonal = (() => {
    try { return getSeasonalContext(lang) }
    catch(e) { return { banner: null, bannerIcon: null, suggestions: [], seasonalProduce: [], event: null } }
  })()
  const greeting = (() => {
    try { return getGreeting(lang) }
    catch(e) { return 'Welcome 👋' }
  })()
  const isGtin   = /^\d{8,14}$/.test(query.trim())
  const dinner   = DINNERS[new Date().getDay() % DINNERS.length]

  // Load promotions
  useEffect(() => {
    api.promotions({ limit: 3, lang }).then(d => setPromotions(d.promotions || [])).catch(() => {})
  }, [])

  // Search as user types
  useEffect(() => {
    if (!query.trim() || isGtin) { setResults([]); return }
    const t = setTimeout(async () => {
      setLoading(true)
      try {
        track('search', { query })
        const res = await api.search({ q: query, lang, limit: 8 })
        setResults(res.results || [])
      } catch(e) {
        console.error('Search error:', e)
      } finally {
        setLoading(false)
      }
    }, 300)
    return () => clearTimeout(t)
  }, [query])

  const handleAdd = (product) => {
    track('add', { gtin: product.gtin, name: product.name, store: product.store })
    addProduct(product)
    navigate('/basket')
  }

  const startVoice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return
    const r = new SR()
    r.lang = lang === 'de' ? 'de-CH' : lang === 'fr' ? 'fr-CH' : lang === 'it' ? 'it-CH' : 'en-US'
    r.onresult = e => setQuery(e.results[0][0].transcript)
    r.onend    = () => setListening(false)
    r.start()
    setListening(true)
  }

  const clearSearch = () => {
    setQuery('')
    setResults([])
    inputRef.current?.focus()
  }

  return (
    <div style={{ paddingBottom: 90 }}>

      {/* Greeting */}
      <div style={{ padding: '20px 16px 0' }}>
        <p style={{ fontSize: 13, color: 'var(--muted)', margin: '0 0 4px' }}>
          {new Date().toLocaleDateString(
            lang === 'de' ? 'de-CH' : lang === 'fr' ? 'fr-CH' : lang === 'it' ? 'it-CH' : 'en-GB',
            { weekday: 'long', day: 'numeric', month: 'long' }
          )}
        </p>
        <h1 style={{ fontFamily: 'Syne', fontSize: 24, fontWeight: 800, margin: 0 }}>
          {greeting}
        </h1>
      </div>

      {/* Quick actions */}
      <div style={{ display: 'flex', gap: 8, padding: '14px 16px 0' }}>
        {[
          { icon:'📍', label:'Nearby',  path:'/stores' },
          { icon:'💬', label:'Ask AI',  path:'/chat'   },
          { icon:'📷', label:'Scan',    path:'/scan'   },
        ].map(({ icon, label, path }) => (
          <button key={path} onClick={() => navigate(path)} style={{
            flex: 1, padding: '10px 4px',
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 12, cursor: 'pointer',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
          }}>
            <span style={{ fontSize: 20 }}>{icon}</span>
            <span style={{ fontSize: 10, color: 'var(--muted)' }}>{label}</span>
          </button>
        ))}
      </div>

      {/* Seasonal banner */}
      {seasonal.banner && (
        <div style={{
          margin: '14px 16px 0', padding: '12px 16px',
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 14, display: 'flex', alignItems: 'center', gap: 12,
          cursor: 'pointer',
        }} onClick={() => { setQuery(seasonal.suggestions?.[0] || ''); inputRef.current?.focus() }}>
          <span style={{ fontSize: 24 }}>{seasonal.bannerIcon}</span>
          <div style={{ flex: 1 }}>
            <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>{seasonal.banner}</p>
            {seasonal.seasonalProduce?.length > 0 && (
              <p style={{ margin: '2px 0 0', fontSize: 11, color: 'var(--muted)' }}>
                🇨🇭 In season: {seasonal.seasonalProduce.slice(0, 3).join(' · ')}
              </p>
            )}
          </div>
          <span style={{ fontSize: 11, color: 'var(--red)', fontWeight: 600 }}>Shop →</span>
        </div>
      )}

      {/* Search box */}
      <div style={{ padding: '14px 16px 0' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'var(--surface)',
          border: `1px solid ${focused ? 'var(--red)' : 'var(--border)'}`,
          borderRadius: 14, padding: '0 12px',
          transition: 'border-color 0.15s',
        }}>
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            onKeyDown={e => {
              if (e.key === 'Enter' && isGtin) navigate(`/product/${query.trim()}`)
            }}
            placeholder={{
              en: 'Search products...', de: 'Produkte suchen...',
              fr: 'Rechercher...', it: 'Cerca...',
            }[lang] || 'Search products...'}
            style={{
              flex: 1, background: 'none', border: 'none', outline: 'none',
              padding: '14px 0', fontSize: 15, color: 'var(--text)',
            }}
          />
          {query ? (
            <button onClick={clearSearch} style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--muted)', padding: 4,
            }}>
              <X size={16} />
            </button>
          ) : null}
          <button onClick={startVoice} style={{
            background: listening ? 'var(--red)' : 'none',
            border: 'none', cursor: 'pointer', borderRadius: 8, padding: 6,
            color: listening ? 'white' : 'var(--muted)',
          }}>
            <Mic size={17} />
          </button>
          <button onClick={() => navigate('/scan')} style={{
            background: 'var(--red)', border: 'none', cursor: 'pointer',
            borderRadius: 8, padding: 6,
            display: 'flex', alignItems: 'center',
          }}>
            <ScanLine size={17} color="white" />
          </button>
        </div>

        {/* GTIN hint */}
        {isGtin && (
          <div onClick={() => navigate(`/product/${query.trim()}`)} style={{
            marginTop: 8, padding: '8px 14px',
            background: 'rgba(230,57,70,0.08)',
            border: '1px solid rgba(230,57,70,0.3)',
            borderRadius: 10, fontSize: 13, color: 'var(--red)', cursor: 'pointer',
          }}>
            📦 Barcode detected — tap to view product →
          </div>
        )}

        {/* Suggestions — when focused and no query */}
        {focused && !query && seasonal.suggestions?.length > 0 && (
          <div style={{
            marginTop: 8, background: 'var(--surface)',
            border: '1px solid var(--border)', borderRadius: 14,
            padding: '12px 14px',
          }}>
            <p style={{ margin: '0 0 10px', fontSize: 11, color: 'var(--muted)', fontWeight: 600 }}>
              {seasonal.event ? `${seasonal.bannerIcon} ${seasonal.event.name}` : '💡 Suggestions'}
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {seasonal.suggestions.slice(0, 6).map(s => (
                <button key={s} onClick={() => { setQuery(s); setFocused(false) }} style={{
                  padding: '6px 14px', borderRadius: 20,
                  border: '1px solid var(--border)',
                  background: 'var(--dark)', fontSize: 13,
                  cursor: 'pointer', color: 'var(--text)', textTransform: 'capitalize',
                }}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ padding: '12px 16px 0' }}>
          <div className="skeleton" style={{ height: 60, borderRadius: 14 }} />
        </div>
      )}

      {/* Search results */}
      {results.length > 0 && (
        <div style={{ padding: '12px 16px 0' }}>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10, fontWeight: 500 }}>
            {results.length} results for "{query}"
          </p>
          {results.map((p, i) => (
            <div key={`${p.gtin}-${p.store}-${i}`}
              onClick={() => navigate(`/product/${p.gtin}`)}
              style={{ marginBottom: 8, cursor: 'pointer' }}>
              <div className="card" style={{
                display: 'flex', gap: 12, alignItems: 'center', padding: '12px 14px',
              }}>
                {p.image_url && (
                  <img src={p.image_url} alt={p.name}
                    style={{ width: 48, height: 48, objectFit: 'contain',
                             borderRadius: 8, flexShrink: 0 }}
                    onError={e => e.target.style.display = 'none'}
                  />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{
                    margin: 0, fontWeight: 600, fontSize: 14,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {p.name || p.name_en || p.name_de || 'Unknown'}
                  </p>
                  <p style={{ margin: '2px 0 0', fontSize: 12,
                               color: STORE_COLORS[p.store] || 'var(--muted)' }}>
                    ● {p.store}{p.brand ? ` · ${p.brand}` : ''}
                  </p>
                </div>
                {p.price && (
                  <span style={{ fontWeight: 700, fontSize: 14, flexShrink: 0 }}>
                    CHF {Number(p.price).toFixed(2)}
                  </span>
                )}
                <span style={{ fontSize: 18, color: 'var(--muted)' }}>›</span>
              </div>
            </div>
          ))}
          <button onClick={clearSearch} style={{
            width: '100%', padding: '10px', borderRadius: 12, marginTop: 4,
            border: '1px solid var(--border)', background: 'none',
            color: 'var(--muted)', fontSize: 13, cursor: 'pointer',
          }}>
            Clear search ×
          </button>
        </div>
      )}

      {/* Content when no search */}
      {!query && (
        <>
          {/* Dinner suggestion */}
          <div style={{ padding: '20px 16px 0' }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 12px' }}>
              🍽️ Tonight's dinner idea
            </h2>
            <div className="card" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12 }}
              onClick={() => { setQuery(dinner.search); inputRef.current?.focus() }}>
              <span style={{ fontSize: 36 }}>{dinner.icon}</span>
              <div style={{ flex: 1 }}>
                <p style={{ margin: 0, fontWeight: 600, fontSize: 15 }}>{dinner.name}</p>
                <p style={{ margin: '3px 0 0', fontSize: 12, color: 'var(--muted)' }}>
                  Tap to find ingredients →
                </p>
              </div>
              <span style={{ fontSize: 11, color: 'var(--red)', fontWeight: 600 }}>Shop →</span>
            </div>
          </div>

          {/* Deals */}
          {promotions.length > 0 && (
            <div style={{ padding: '20px 16px 0' }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 12px' }}>🔥 Today's deals</h2>
              {promotions.map((promo, i) => {
                const color = STORE_COLORS[promo.store] || 'var(--muted)'
                return (
                  <div key={i} className="card animate-in" style={{
                    marginBottom: 10, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 12,
                  }} onClick={() => navigate(`/product/${promo.gtin}`)}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{
                        margin: 0, fontSize: 14, fontWeight: 600,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>{promo.name}</p>
                      <p style={{ margin: '2px 0 0', fontSize: 12, color }}>
                        ● {promo.store} · {promo.promotion_label}
                      </p>
                    </div>
                    <div style={{ textAlign: 'right', flexShrink: 0 }}>
                      <p style={{ margin: 0, fontFamily: 'Syne', fontWeight: 700, fontSize: 15 }}>
                        CHF {promo.promo_price_chf?.toFixed(2)}
                      </p>
                      <p style={{ margin: 0, fontSize: 11, color: 'var(--muted)', textDecoration: 'line-through' }}>
                        CHF {promo.original_price_chf?.toFixed(2)}
                      </p>
                    </div>
                    <div style={{
                      background: 'rgba(45,198,83,0.12)', color: '#4ade80',
                      borderRadius: 8, padding: '4px 8px',
                      fontSize: 12, fontWeight: 700, flexShrink: 0,
                    }}>
                      -{promo.discount_pct?.toFixed(0)}%
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Privacy note */}
          {!localStorage.getItem('privacy_shown') && (
            <div style={{
              margin: '20px 16px 0', padding: '12px 16px',
              background: 'var(--surface)', border: '1px solid var(--border)',
              borderRadius: 14, display: 'flex', gap: 10, alignItems: 'flex-start',
            }}>
              <span style={{ fontSize: 18, flexShrink: 0 }}>🔒</span>
              <div style={{ flex: 1 }}>
                <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>Your data stays yours</p>
                <p style={{ margin: '3px 0 0', fontSize: 12, color: 'var(--muted)', lineHeight: 1.5 }}>
                  WiseMarket never sells your shopping data. Delete everything anytime in Profile.
                </p>
              </div>
              <button onClick={() => {
                localStorage.setItem('privacy_shown', '1')
                document.querySelector('[data-privacy]')?.remove()
              }} style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--muted)', fontSize: 20, padding: 0, flexShrink: 0,
              }}>×</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
