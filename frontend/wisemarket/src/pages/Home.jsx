import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mic, ScanLine, Send, X } from 'lucide-react'
import { api } from '../api/client'
import { useBasket } from '../hooks/useBasket'
import { getSeasonalContext, getGreeting, getCarbonScore } from '../data/seasonal'
import { track, getSmartSuggestions, getFrequentProducts } from '../hooks/useTracking'
import ProductCard from '../components/ProductCard'

export default function Home() {
  const navigate = useNavigate()
  const { addProduct } = useBasket()
  const lang = localStorage.getItem('lang') || 'en'

  const [query, setQuery]             = useState('')
  const [focused, setFocused]         = useState(false)
  const [results, setResults]         = useState([])
  const [aiResponse, setAiResponse]   = useState(null)
  const [loading, setLoading]         = useState(false)
  const [promotions, setPromotions]   = useState([])
  const [listening, setListening]     = useState(false)
  const [mode, setMode]               = useState('search') // search | ai
  const inputRef = useRef()

  const seasonal = getSeasonalContext(lang)
  const greeting = getGreeting(lang)
  const isGtin = /^\d{8,14}$/.test(query.trim())

  // Load promotions
  useEffect(() => {
    api.promotions({ limit: 3, lang }).then(d => setPromotions(d.promotions || [])).catch(() => {})
  }, [])

  // Search as user types
  useEffect(() => {
    if (!query.trim()) { setResults([]); return }
    if (isGtin) return
    const t = setTimeout(async () => {
      setLoading(true)
      track('search', { query })
      try {
        const dietary = JSON.parse(localStorage.getItem('dietary') || '{}')
        // Only pass filters that are explicitly TRUE
        const VALID_FILTERS = ['halal','vegan','vegetarian','gluten_free','lactose_free',
          'dairy_free','nut_free','organic','regional','high_protein','low_sugar']
        const filters = {}
        VALID_FILTERS.forEach(k => { if (dietary[k] === true) filters[k] = true })
        const res = await api.search({ q: query, lang, limit: 8, ...filters })
        setResults(res.results || [])
      } catch(e) {}
      finally { setLoading(false) }
    }, 300)
    return () => clearTimeout(t)
  }, [query])

  const handleSubmit = async () => {
    if (!query.trim()) return
    if (isGtin) { navigate(`/product/${query.trim()}`); return }

    if (isAiQuery(query)) {
      setLoading(true)
      setAiResponse(null)
      try {
        const res = await api.query({ input: query, lang, mode: 'chat' })
        setAiResponse(res)
        setResults(res.products || [])
      } catch(e) {}
      finally { setLoading(false) }
    }
  }

  const handleSuggestion = (s) => {
    setQuery(s)
    setFocused(true)
    inputRef.current?.focus()
  }

  const handleAdd = (product) => {
    track('add', { gtin: product.gtin, name: product.name || product.name_en, category: product.category, store: product.store })
    addProduct(product)
    navigate('/basket')
  }

  const startVoice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return
    const r = new SR()
    r.lang = lang === 'de' ? 'de-CH' : lang === 'fr' ? 'fr-CH' : lang === 'it' ? 'it-CH' : 'en-US'
    r.onresult = e => { setQuery(e.results[0][0].transcript); setFocused(true) }
    r.onend = () => setListening(false)
    r.start()
    setListening(true)
  }

  const showSuggestions = focused && !query && seasonal.suggestions?.length > 0
  const showResults = results.length > 0
  const showAI = aiResponse && !loading

  return (
    <div style={{ paddingBottom: 90 }}>

      {/* Header with greeting */}
      <div style={{ padding: '20px 16px 0' }}>
        <p style={{ fontSize: 13, color: 'var(--muted)', margin: '0 0 4px' }}>
          {new Date().toLocaleDateString(lang === 'de' ? 'de-CH' : lang === 'fr' ? 'fr-CH' : lang === 'it' ? 'it-CH' : 'en-GB',
            { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
        <h1 style={{ fontFamily: 'Syne', fontSize: 24, fontWeight: 800, margin: 0 }}>
          {greeting}
        </h1>
      </div>

      {/* Quick actions row */}
      <div style={{ display: 'flex', gap: 8, padding: '14px 16px 0' }}>
        {[
          { icon: '📍', label: { en:'Nearby', de:'In der Nähe', fr:'À proximité', it:'Vicino' }, path: '/stores' },
          { icon: '🔥', label: { en:'Deals', de:'Angebote', fr:'Offres', it:'Offerte' }, path: '/deals' },
          { icon: '💬', label: { en:'Ask AI', de:'KI fragen', fr:'Demander', it:'Chiedi' }, path: '/chat' },
          { icon: '📷', label: { en:'Scan', de:'Scannen', fr:'Scanner', it:'Scansiona' }, path: '/scan' },
        ].map(({ icon, label, path }) => (
          <button key={path} onClick={() => navigate(path)} style={{
            flex: 1, padding: '10px 4px', background: 'var(--surface)',
            border: '1px solid var(--border)', borderRadius: 12, cursor: 'pointer',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
            transition: 'border-color 0.15s',
          }}
            onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--red)'}
            onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
          >
            <span style={{ fontSize: 20 }}>{icon}</span>
            <span style={{ fontSize: 10, color: 'var(--muted)' }}>{label[lang] || label.en}</span>
          </button>
        ))}
      </div>

      {/* Seasonal banner */}
      {seasonal.banner && (
        <div style={{
          margin: '14px 16px 0',
          padding: '12px 16px',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 14,
          cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 12,
        }}
          onClick={() => handleSuggestion(seasonal.suggestions?.[0] || '')}
        >
          <span style={{ fontSize: 24, flexShrink: 0 }}>{seasonal.bannerIcon}</span>
          <div style={{ flex: 1 }}>
            <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>{seasonal.banner}</p>
            {seasonal.seasonalProduce?.length > 0 && (
              <p style={{ margin: '2px 0 0', fontSize: 11, color: 'var(--muted)' }}>
                🇨🇭 In season now: {seasonal.seasonalProduce.slice(0, 3).join(' · ')}
              </p>
            )}
          </div>
          <span style={{ fontSize: 11, color: 'var(--red)', fontWeight: 600, flexShrink: 0 }}>
            Shop →
          </span>
        </div>
      )}

      {/* Smart search box */}
      <div style={{ padding: '14px 16px 0', position: 'relative' }}>

        {/* Mode toggle */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 8,
                      background: 'var(--surface)', borderRadius: 10, padding: 3, width: 'fit-content' }}>
          {[['search','🔍 Search'], ['ai','✨ Ask AI']].map(([m, label]) => (
            <button key={m} onClick={() => setMode(m)} style={{
              padding: '5px 14px', border: 'none', borderRadius: 8, fontSize: 12,
              background: mode === m ? 'var(--dark)' : 'transparent',
              color: mode === m ? 'var(--text)' : 'var(--muted)',
              fontWeight: mode === m ? 600 : 400, cursor: 'pointer',
            }}>{label}</button>
          ))}
        </div>

        {/* Input */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'var(--surface)', border: `1px solid ${focused ? 'var(--red)' : 'var(--border)'}`,
          borderRadius: 14, padding: '0 12px', transition: 'border-color 0.15s',
        }}>
          <input ref={inputRef} value={query}
            onChange={e => setQuery(e.target.value)}
            onFocus={() => setFocused(true)}

            onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            placeholder={mode === 'ai'
              ? { en: 'Ask anything — prices, halal, nutrition...', de: 'Fragen Sie alles — Preise, Halal, Nährwerte...', fr: 'Demandez tout — prix, halal, nutrition...', it: 'Chiedi tutto — prezzi, halal, nutrizione...' }[lang] || 'Ask anything...'
              : { en: 'Search products or scan barcode...', de: 'Produkte suchen oder Barcode scannen...', fr: 'Rechercher ou scanner...', it: 'Cerca o scansiona...' }[lang] || 'Search...'
            }
            style={{ flex: 1, background: 'none', border: 'none', outline: 'none',
                     padding: '14px 0', fontSize: 15, color: 'var(--text)' }}
          />
          {query ? (
            <button onClick={() => { setQuery(''); setResults([]); setAiResponse(null); setFocused(false) }}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: 4 }}>
              <X size={16} />
            </button>
          ) : null}
          <button onClick={startVoice} style={{
            background: listening ? 'var(--red)' : 'none', border: 'none',
            cursor: 'pointer', borderRadius: 8, padding: 6,
            color: listening ? 'white' : 'var(--muted)',
          }}>
            <Mic size={17} />
          </button>
          <button onClick={() => navigate('/scan')} style={{
            background: 'var(--red)', border: 'none', cursor: 'pointer',
            borderRadius: 8, padding: 6, display: 'flex', alignItems: 'center',
          }}>
            <ScanLine size={17} color="white" />
          </button>
          {query && (
            <button onClick={handleSubmit} style={{
              background: 'var(--red)', border: 'none', cursor: 'pointer',
              borderRadius: 8, padding: 6, display: 'flex', alignItems: 'center',
            }}>
              <Send size={15} color="white" />
            </button>
          )}
        </div>

        {/* GTIN hint */}
        {isGtin && (
          <div onClick={() => navigate(`/product/${query.trim()}`)} style={{
            marginTop: 8, padding: '8px 14px', background: 'rgba(230,57,70,0.08)',
            border: '1px solid rgba(230,57,70,0.3)', borderRadius: 10,
            fontSize: 13, color: 'var(--red)', cursor: 'pointer',
          }}>
            📦 GTIN detected — tap to view product →
          </div>
        )}

        {/* Suggestions dropdown */}
        {showSuggestions && (
          <div style={{
            position: 'absolute', top: 'calc(100% - 4px)', left: 16, right: 16,
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 14, zIndex: 50, overflow: 'hidden',
            boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
          }}>
            <div style={{ padding: '10px 14px 6px' }}>
              <p style={{ margin: 0, fontSize: 11, color: 'var(--muted)', fontWeight: 600 }}>
                {seasonal.event ? `${seasonal.bannerIcon} ${seasonal.event.name}` :
                 seasonal.isWeekend ? '🏡 Weekend ideas' : '💡 Suggestions'}
              </p>
            </div>
            <div style={{ display: 'flex', gap: 8, padding: '0 14px 12px',
                          overflowX: 'auto', scrollbarWidth: 'none' }}>
              {seasonal.suggestions.map(s => (
                <button key={s} onClick={() => handleSuggestion(s)} style={{
                  whiteSpace: 'nowrap', padding: '6px 14px', borderRadius: 20,
                  border: '1px solid var(--border)', background: 'var(--dark)',
                  fontSize: 13, cursor: 'pointer', color: 'var(--text)',
                  textTransform: 'capitalize',
                }}>
                  {s}
                </button>
              ))}
            </div>

            {/* Seasonal produce */}
            {seasonal.seasonalProduce?.length > 0 && (
              <>
                <div style={{ borderTop: '1px solid var(--border)', padding: '8px 14px 6px' }}>
                  <p style={{ margin: 0, fontSize: 11, color: 'var(--muted)', fontWeight: 600 }}>
                    🇨🇭 In season this month
                  </p>
                </div>
                <div style={{ display: 'flex', gap: 8, padding: '0 14px 12px',
                              overflowX: 'auto', scrollbarWidth: 'none' }}>
                  {seasonal.seasonalProduce.map(s => (
                    <button key={s} onClick={() => handleSuggestion(s)} style={{
                      whiteSpace: 'nowrap', padding: '6px 14px', borderRadius: 20,
                      border: '1px solid rgba(45,198,83,0.3)',
                      background: 'rgba(45,198,83,0.08)',
                      fontSize: 13, cursor: 'pointer', color: '#4ade80',
                      textTransform: 'capitalize',
                    }}>
                      🌱 {s}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* AI response */}
      {showAI && (
        <div style={{ margin: '12px 16px 0' }} className="animate-in">
          <div className="card">
            <p style={{ fontSize: 12, color: 'var(--red)', fontWeight: 600, marginBottom: 8 }}>
              ✨ AI · {aiResponse.intent?.replace('_', ' ')}
            </p>
            <p style={{ fontSize: 14, lineHeight: 1.6 }}>{aiResponse.response}</p>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{ margin: '12px 16px 0' }}>
          <div className="skeleton" style={{ height: 60, borderRadius: 14 }} />
        </div>
      )}

      {/* Search results */}
      {results.length > 0 && (
        <div style={{ padding: '12px 16px 0' }}>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>
            {results.length} {lang === 'de' ? 'Ergebnisse' : lang === 'fr' ? 'résultats' : lang === 'it' ? 'risultati' : 'results'} for "{query}"
          </p>
          <div>
            {results.map((p, i) => (
              <div key={`${p.gtin}-${p.store}-${i}`}
                style={{ marginBottom: 8, cursor: 'pointer' }}
                onClick={() => navigate(`/product/${p.gtin}`)}>
                <div className="card" style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  {p.image_url && (
                    <img src={p.image_url} alt={p.name}
                      style={{ width: 48, height: 48, borderRadius: 8, objectFit: 'contain', flexShrink: 0 }}
                      onError={e => e.target.style.display='none'}
                    />
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ margin: 0, fontWeight: 600, fontSize: 14,
                                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {p.name || p.name_en || p.name_de}
                    </p>
                    <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--muted)' }}>
                      {p.brand && `${p.brand} · `}{p.store} · {p.category}
                    </p>
                  </div>
                  {p.price && (
                    <span style={{ fontWeight: 700, fontSize: 14, flexShrink: 0 }}>
                      CHF {Number(p.price).toFixed(2)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Dinner suggestion — show always for testing, normally after 16:00 */}
      {!query && (
        <div style={{ padding: '20px 16px 0' }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 12px' }}>
            🍽️ Tonight's dinner idea
          </h2>
          {(() => {
            const day = new Date().getDay()
            const dinners = [
              { icon:'🍕', name:'Pizza night',     search:'mozzarella tomaten pizza' },
              { icon:'🍝', name:'Pasta bolognese', search:'hackfleisch pasta tomaten' },
              { icon:'🥗', name:'Light salad',     search:'salat lachs avocado' },
              { icon:'🐟', name:'Salmon & veg',    search:'lachs gemüse zitrone' },
              { icon:'🧀', name:'Raclette evening',search:'raclettekäse kartoffeln cornichons' },
              { icon:'🍲', name:'Fondue night',    search:'fonduekäse brot weisswein' },
              { icon:'🐔', name:'Roast chicken',   search:'poulet kartoffeln kräuter' },
            ]
            const d = dinners[day % dinners.length]
            return (
              <div className="card" style={{ cursor: 'pointer' }}
                onClick={() => {
                  setQuery(d.search)
                  inputRef.current?.focus()
                }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 32 }}>{d.icon}</span>
                  <div style={{ flex: 1 }}>
                    <p style={{ margin: 0, fontWeight: 600, fontSize: 14 }}>{d.name}</p>
                    <p style={{ margin: '3px 0 0', fontSize: 12, color: 'var(--muted)' }}>
                      Tap to find ingredients →
                    </p>
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--red)', fontWeight: 600 }}>Shop →</span>
                </div>
              </div>
            )
          })()}
        </div>
      )}

      {/* Today's deals — shown when no search active */}
      {!query && promotions.length > 0 && (
        <div style={{ padding: '20px 16px 0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between',
                        alignItems: 'center', marginBottom: 12 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>🔥 Today's deals</h2>
            <button onClick={() => navigate('/deals')} style={{
              background: 'none', border: 'none', color: 'var(--red)',
              fontSize: 13, cursor: 'pointer', fontWeight: 500,
            }}>See all</button>
          </div>
          {promotions.map((promo, i) => {
            const STORE_COLORS = { migros:'#E05A00', coop:'#C0001A', aldi:'#00539F', lidl:'#0050AA' }
            const color = STORE_COLORS[promo.store] || 'var(--muted)'
            return (
              <div key={i} className="card animate-in" style={{
                marginBottom: 10, cursor: 'pointer', display: 'flex',
                alignItems: 'center', gap: 12, animationDelay: `${i*0.08}s`,
              }} onClick={() => navigate(`/product/${promo.gtin}`)}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ margin: 0, fontSize: 14, fontWeight: 600,
                               overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {promo.name}
                  </p>
                  <p style={{ margin: '2px 0 0', fontSize: 12, color }}>
                    ● {promo.store} · {promo.promotion_label}
                  </p>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <p style={{ margin: 0, fontFamily: 'Syne', fontWeight: 700, fontSize: 15 }}>
                    CHF {promo.promo_price_chf?.toFixed(2)}
                  </p>
                  <p style={{ margin: 0, fontSize: 11, color: 'var(--muted)',
                               textDecoration: 'line-through' }}>
                    CHF {promo.original_price_chf?.toFixed(2)}
                  </p>
                </div>
                <div style={{
                  background: 'rgba(45,198,83,0.12)', color: '#4ade80',
                  borderRadius: 8, padding: '4px 8px', fontSize: 12, fontWeight: 700,
                  flexShrink: 0,
                }}>
                  -{promo.discount_pct?.toFixed(0)}%
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Privacy note — shown once */}
      {!localStorage.getItem('privacy_shown') && (
        <div style={{ margin: '20px 16px 0', padding: '12px 16px',
                      background: 'var(--surface)', border: '1px solid var(--border)',
                      borderRadius: 14, display: 'flex', gap: 10, alignItems: 'flex-start' }}>
          <span style={{ fontSize: 18, flexShrink: 0 }}>🔒</span>
          <div style={{ flex: 1 }}>
            <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>Your data stays yours</p>
            <p style={{ margin: '3px 0 0', fontSize: 12, color: 'var(--muted)', lineHeight: 1.5 }}>
              WiseMarket never sells your shopping data. Delete everything anytime in Profile.
            </p>
          </div>
          <button onClick={() => { localStorage.setItem('privacy_shown','1'); }} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--muted)', fontSize: 18, padding: 0, flexShrink: 0,
          }}>×</button>
        </div>
      )}

    </div>
  )
}
