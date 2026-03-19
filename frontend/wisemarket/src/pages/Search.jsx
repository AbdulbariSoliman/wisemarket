import { useState, useEffect, useRef } from 'react'
import { Search as SearchIcon, X, Send, Mic } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import ProductCard from '../components/ProductCard'

const FILTERS = ['halal','vegan','gluten_free','lactose_free','organic','high_protein','low_sugar','vegetarian','dairy_free']
const FILTER_LABELS = {
  halal:'☪️ Halal', vegan:'🌱 Vegan', gluten_free:'🌾 GF',
  lactose_free:'🥛 LF', organic:'🌿 Bio', high_protein:'💪 Protein',
  low_sugar:'🍬 Low Sugar', vegetarian:'🥦 Veg', dairy_free:'DF Dairy-Free',
}

const GTIN_RE = /^\d{8,14}$/

export default function Search() {
  const navigate = useNavigate()
  const [query, setQuery]       = useState('')
  const [active, setActive]     = useState({})
  const [results, setResults]   = useState([])
  const [loading, setLoading]   = useState(false)
  const [total, setTotal]       = useState(0)
  const [mode, setMode]         = useState('search') // 'search' | 'chat'
  const [messages, setMessages] = useState([])
  const [chatLoading, setChatLoading] = useState(false)
  const [listening, setListening]     = useState(false)
  const inputRef  = useRef()
  const bottomRef = useRef()
  const lang = localStorage.getItem('lang') || 'en'

  // Auto-detect GTIN
  const isGtin = GTIN_RE.test(query.trim())

  useEffect(() => {
    if (mode === 'chat') return
    if (isGtin) {
      // Direct GTIN lookup
      navigate(`/product/${query.trim()}`)
      return
    }
    const t = setTimeout(() => doSearch(), 350)
    return () => clearTimeout(t)
  }, [query, active, mode])

  useEffect(() => {
    doSearch('', {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const doSearch = async (q = query, filters = active) => {
    if (mode === 'chat') return
    setLoading(true)
    try {
      const params = { q: q || undefined, lang, limit: 20,
                       ...Object.fromEntries(Object.entries(filters).filter(([,v]) => v)) }
      const data = await api.search(params)
      setResults(data.results || [])
      setTotal(data.count || 0)
    } catch(e) { console.error(e) }
    finally { setLoading(false) }
  }

  const sendChat = async (text) => {
    if (!text.trim()) return
    const userMsg = { role: 'user', text }
    setMessages(m => [...m, userMsg])
    setQuery('')
    setChatLoading(true)
    try {
      const res = await api.query({ input: text, lang, mode: 'chat' })
      setMessages(m => [...m, {
        role: 'assistant', text: res.response,
        products: res.products, intent: res.intent,
      }])
    } catch(e) {
      setMessages(m => [...m, { role: 'assistant', text: 'Something went wrong.' }])
    } finally { setChatLoading(false) }
  }

  const handleSubmit = () => {
    if (mode === 'chat') sendChat(query)
    else if (isGtin) navigate(`/product/${query.trim()}`)
  }

  const startVoice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return
    const r = new SR()
    r.lang = lang === 'de' ? 'de-CH' : lang === 'fr' ? 'fr-CH' : lang === 'it' ? 'it-CH' : 'en-US'
    r.onresult = e => {
      const t = e.results[0][0].transcript
      setQuery(t)
      if (mode === 'chat') sendChat(t)
    }
    r.onend = () => setListening(false)
    r.start()
    setListening(true)
  }

  const toggleFilter = (f) =>
    setActive(prev => ({ ...prev, [f]: prev[f] ? undefined : true }))

  return (
    <div style={{ padding: '24px 16px 100px' }}>
      <h1 style={{ fontFamily: 'Syne', fontSize: 24, fontWeight: 800, marginBottom: 16 }}>
        Search
      </h1>

      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 14,
                    background: 'var(--surface)', borderRadius: 12, padding: 4 }}>
        {[['search','🔍 Products'], ['chat','💬 Ask AI']].map(([m, label]) => (
          <button key={m} onClick={() => { setMode(m); setQuery('') }} style={{
            flex: 1, padding: '8px 0', border: 'none', borderRadius: 8,
            background: mode === m ? 'var(--dark)' : 'transparent',
            color: mode === m ? 'var(--text)' : 'var(--muted)',
            fontWeight: mode === m ? 600 : 400, fontSize: 13,
            cursor: 'pointer', transition: 'all 0.15s',
          }}>
            {label}
          </button>
        ))}
      </div>

      {/* Input */}
      <div style={{ position: 'relative', marginBottom: 14 }}>
        <SearchIcon size={18} color="var(--muted)" style={{
          position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)'
        }} />
        <input ref={inputRef} value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          placeholder={mode === 'chat'
            ? 'Ask anything — halal options, price check, vegan pasta...'
            : isGtin ? `GTIN detected — press Enter to look up`
            : 'Search products, brands, GTINs...'}
          style={{ paddingLeft: 44, paddingRight: 80,
                   borderColor: isGtin ? 'var(--red)' : undefined }}
        />
        <div style={{ position: 'absolute', right: 8, top: '50%',
                      transform: 'translateY(-50%)', display: 'flex', gap: 4 }}>
          {query && (
            <button onClick={() => setQuery('')} style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--muted)', padding: 4,
            }}>
              <X size={16} />
            </button>
          )}
          <button onClick={startVoice} style={{
            background: listening ? 'var(--red)' : 'none',
            border: 'none', cursor: 'pointer',
            color: listening ? 'white' : 'var(--muted)',
            borderRadius: 8, padding: 4,
          }}>
            <Mic size={16} />
          </button>
          {(mode === 'chat' || isGtin) && query && (
            <button onClick={handleSubmit} style={{
              background: 'var(--red)', border: 'none', cursor: 'pointer',
              borderRadius: 8, padding: '4px 8px', color: 'white',
            }}>
              <Send size={14} />
            </button>
          )}
        </div>
      </div>

      {/* GTIN hint */}
      {isGtin && mode === 'search' && (
        <div style={{ background: 'rgba(230,57,70,0.08)',
                      border: '1px solid rgba(230,57,70,0.3)',
                      borderRadius: 12, padding: '10px 14px', marginBottom: 14,
                      fontSize: 13, color: 'var(--red)', cursor: 'pointer' }}
          onClick={() => navigate(`/product/${query.trim()}`)}>
          📦 GTIN detected — tap to view product →
        </div>
      )}

      {/* Filters — only in search mode */}
      {mode === 'search' && (
        <div style={{ display: 'flex', gap: 8, overflowX: 'auto',
                      paddingBottom: 4, marginBottom: 16, scrollbarWidth: 'none' }}>
          {FILTERS.map(f => (
            <button key={f} onClick={() => toggleFilter(f)} style={{
              whiteSpace: 'nowrap', padding: '6px 12px', borderRadius: 20,
              border: `1px solid ${active[f] ? 'var(--red)' : 'var(--border)'}`,
              background: active[f] ? 'rgba(230,57,70,0.12)' : 'var(--surface)',
              color: active[f] ? 'var(--red)' : 'var(--muted)',
              fontSize: 12, fontWeight: active[f] ? 600 : 400,
              cursor: 'pointer', transition: 'all 0.15s',
            }}>
              {FILTER_LABELS[f]}
            </button>
          ))}
        </div>
      )}

      {/* Search results */}
      {mode === 'search' && (
        <>
          {!loading && (
            <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 14 }}>
              {total} product{total !== 1 ? 's' : ''} found
            </p>
          )}
          {loading
            ? [1,2,3,4].map(i => (
                <div key={i} className="skeleton"
                  style={{ height: 88, marginBottom: 10, borderRadius: 16 }} />
              ))
            : results.map((p, i) => (
                <div key={`${p.gtin}-${p.store}`} style={{ animationDelay: `${i*0.04}s` }}>
                  <ProductCard product={p} />
                </div>
              ))
          }
          {!loading && results.length === 0 && (
            <div style={{ textAlign: 'center', padding: '50px 20px', color: 'var(--muted)' }}>
              <p style={{ fontSize: 36, marginBottom: 10 }}>🔍</p>
              <p style={{ fontWeight: 600, marginBottom: 6 }}>No results</p>
              <p style={{ fontSize: 13 }}>Try switching to AI chat for smart suggestions</p>
              <button onClick={() => setMode('chat')} style={{
                marginTop: 12, background: 'var(--red)', border: 'none',
                color: 'white', borderRadius: 10, padding: '8px 20px',
                cursor: 'pointer', fontSize: 13,
              }}>
                Ask AI instead
              </button>
            </div>
          )}
        </>
      )}

      {/* Chat mode */}
      {mode === 'chat' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted)' }}>
              <p style={{ fontSize: 36, marginBottom: 10 }}>💬</p>
              <p style={{ fontWeight: 600, marginBottom: 6 }}>Ask me anything</p>
              {['Where is milk cheapest?', 'Show me halal chicken', 'Vegan pasta options'].map(s => (
                <button key={s} onClick={() => { setQuery(s); sendChat(s) }} style={{
                  display: 'block', width: '100%', marginTop: 8,
                  background: 'var(--surface)', border: '1px solid var(--border)',
                  borderRadius: 10, padding: '10px 16px', cursor: 'pointer',
                  color: 'var(--text)', fontSize: 13, textAlign: 'left',
                  transition: 'border-color 0.15s',
                }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--red)'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className="animate-in" style={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}>
              <div style={{
                maxWidth: '88%',
                background: msg.role === 'user' ? 'var(--red)' : 'var(--surface)',
                border: msg.role === 'assistant' ? '1px solid var(--border)' : 'none',
                borderRadius: msg.role === 'user'
                  ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                padding: '12px 16px',
              }}>
                <p style={{ fontSize: 14, lineHeight: 1.6 }}>{msg.text}</p>
              </div>
            </div>
          ))}

          {/* Product results from chat */}
          {messages[messages.length - 1]?.products?.length > 0 && (
            <div className="animate-in">
              {messages[messages.length - 1].products.slice(0, 3).map((p, i) => (
                <ProductCard key={i} product={p} />
              ))}
            </div>
          )}

          {chatLoading && (
            <div style={{
              display: 'flex', gap: 5, padding: '12px 16px',
              background: 'var(--surface)', borderRadius: '18px 18px 18px 4px',
              width: 'fit-content', border: '1px solid var(--border)',
            }}>
              {[0,1,2].map(i => (
                <div key={i} style={{
                  width: 7, height: 7, borderRadius: '50%',
                  background: 'var(--muted)',
                  animation: `bounce 1s ${i*0.15}s infinite`,
                }} />
              ))}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      <style>{`
        @keyframes bounce {
          0%,100% { transform: translateY(0); }
          50% { transform: translateY(-5px); }
        }
      `}</style>
    </div>
  )
}
