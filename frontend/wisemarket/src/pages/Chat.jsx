import { useState, useRef, useEffect } from 'react'
import { Send, Mic, MicOff } from 'lucide-react'
import { api } from '../api/client'
import ProductCard from '../components/ProductCard'

export default function Chat() {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'Hi! Ask me anything about products, prices, or dietary needs.' }
  ])
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const [listening, setListening] = useState(false)
  const bottomRef = useRef()
  const lang = localStorage.getItem('lang') || 'en'

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text) => {
    if (!text.trim()) return
    const userMsg = { role: 'user', text }
    setMessages(m => [...m, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await api.query({ input: text, lang, mode: 'chat' })
      setMessages(m => [...m, {
        role: 'assistant',
        text: res.response,
        products: res.products || [],
        intent: res.intent,
      }])
    } catch {
      setMessages(m => [...m, { role: 'assistant', text: 'Something went wrong. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  const startVoice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return alert('Voice not supported in this browser')
    const r = new SR()
    r.lang = lang === 'de' ? 'de-CH' : lang === 'fr' ? 'fr-CH' : lang === 'it' ? 'it-CH' : 'en-US'
    r.onresult = e => send(e.results[0][0].transcript)
    r.onend = () => setListening(false)
    r.start()
    setListening(true)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh' }}>
      {/* Header */}
      <div style={{ padding: '20px 16px 12px',
                    borderBottom: '1px solid var(--border)',
                    background: 'var(--dark)' }}>
        <h1 style={{ fontFamily: 'Syne', fontSize: 22, fontWeight: 800 }}>
          💬 Ask WiseMarket
        </h1>
        <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 2 }}>
          Powered by Groq · {lang.toUpperCase()}
        </p>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px',
                    paddingBottom: '80px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{
            display: 'flex',
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            animationDelay: `${i * 0.05}s`,
          }} className="animate-in">
            <div style={{
              maxWidth: '85%',
              background: msg.role === 'user' ? 'var(--red)' : 'var(--surface)',
              border: msg.role === 'assistant' ? '1px solid var(--border)' : 'none',
              borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
              padding: '12px 16px',
            }}>
              <p style={{ fontSize: 14, lineHeight: 1.5 }}>{msg.text}</p>
              {msg.intent && msg.intent !== 'general' && (
                <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', marginTop: 4 }}>
                  {msg.intent.replace('_', ' ')}
                </p>
              )}
            </div>
          </div>
        ))}

        {/* Product results */}
        {messages[messages.length - 1]?.products?.length > 0 && (
          <div className="animate-in">
            {messages[messages.length - 1].products.slice(0, 3).map((p, i) => (
              <ProductCard key={i} product={p} />
            ))}
          </div>
        )}

        {loading && (
          <div style={{ display: 'flex', gap: 4, padding: '12px 16px',
                        background: 'var(--surface)', borderRadius: '18px 18px 18px 4px',
                        width: 'fit-content', border: '1px solid var(--border)' }}>
            {[0,1,2].map(i => (
              <div key={i} style={{
                width: 6, height: 6, borderRadius: '50%', background: 'var(--muted)',
                animation: `bounce 1s ${i * 0.15}s infinite`,
              }} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0,
        padding: '12px 16px calc(12px + env(safe-area-inset-bottom))',
        background: 'rgba(13,13,15,0.95)', backdropFilter: 'blur(20px)',
        borderTop: '1px solid var(--border)',
        display: 'flex', gap: 8, alignItems: 'flex-end',
      }}>
        <input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send(input)}
          placeholder="Ask about products, prices, dietary needs..."
          style={{ borderRadius: 20, paddingLeft: 18, paddingRight: 18, fontSize: 14 }}
        />
        <button onClick={startVoice} style={{
          background: listening ? 'var(--red)' : 'var(--surface)',
          border: '1px solid var(--border)', borderRadius: 12,
          padding: '14px', cursor: 'pointer', flexShrink: 0, transition: 'all 0.15s',
        }}>
          {listening ? <MicOff size={18} color="white" /> : <Mic size={18} color="var(--muted)" />}
        </button>
        <button onClick={() => send(input)} disabled={!input.trim() || loading} style={{
          background: input.trim() ? 'var(--red)' : 'var(--border)',
          border: 'none', borderRadius: 12,
          padding: '14px', cursor: input.trim() ? 'pointer' : 'default',
          flexShrink: 0, transition: 'background 0.15s',
        }}>
          <Send size={18} color="white" />
        </button>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-4px); }
        }
      `}</style>
    </div>
  )
}
