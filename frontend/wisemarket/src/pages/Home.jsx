import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScanLine, Search, Tag, TrendingDown } from 'lucide-react'
import { api } from '../api/client'
import ProductCard from '../components/ProductCard'

export default function Home() {
  const navigate = useNavigate()
  const [greeting, setGreeting] = useState('')
  const [promotions, setPromotions] = useState([])
  const [loading, setLoading] = useState(true)
  const lang = localStorage.getItem('lang') || 'en'

  useEffect(() => {
    Promise.all([
      api.greeting({ lang }),
      api.promotions({ limit: 3 }),
    ]).then(([g, p]) => {
      setGreeting(g.greeting)
      setPromotions(p.promotions || [])
    }).finally(() => setLoading(false))
  }, [])

  const quickActions = [
    { icon: ScanLine,    label: 'Scan',       path: '/scan',   color: 'var(--red)' },
    { icon: Search,      label: 'Search',     path: '/search', color: '#3B82F6'    },
    { icon: Tag,         label: 'Deals',      path: '/deals',  color: '#10B981'    },
    { icon: TrendingDown,label: 'Compare',    path: '/search', color: '#F59E0B'    },
  ]

  return (
    <div style={{ padding: '24px 16px 100px' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }} className="animate-in">
        <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 4 }}>
          {new Date().toLocaleDateString(lang, { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
        <h1 style={{ fontFamily: 'Syne', fontSize: 28, fontWeight: 800,
                     lineHeight: 1.2, marginBottom: 12 }}>
          Wise<span style={{ color: 'var(--red)' }}>Market</span>
        </h1>
        {loading
          ? <div className="skeleton" style={{ height: 40, width: '90%' }} />
          : <p style={{ color: 'var(--muted)', fontSize: 14, lineHeight: 1.5 }}>{greeting}</p>
        }
      </div>

      {/* Quick actions */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
                    gap: 10, marginBottom: 32 }}>
        {quickActions.map(({ icon: Icon, label, path, color }) => (
          <button key={label} onClick={() => navigate(path)} style={{
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 14, padding: '14px 8px', cursor: 'pointer',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
            transition: 'border-color 0.15s, transform 0.15s',
          }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = color; e.currentTarget.style.transform = 'translateY(-2px)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.transform = 'translateY(0)' }}
          >
            <div style={{ background: `${color}22`, borderRadius: 10, padding: 8 }}>
              <Icon size={18} color={color} />
            </div>
            <span style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 500 }}>{label}</span>
          </button>
        ))}
      </div>

      {/* Promotions */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between',
                      alignItems: 'center', marginBottom: 14 }}>
          <h2 style={{ fontSize: 17, fontWeight: 700 }}>🔥 Today's Deals</h2>
          <button onClick={() => navigate('/deals')} style={{
            background: 'none', border: 'none', color: 'var(--red)',
            fontSize: 13, cursor: 'pointer', fontWeight: 500,
          }}>See all</button>
        </div>

        {loading
          ? [1,2,3].map(i => (
              <div key={i} className="skeleton" style={{ height: 80, marginBottom: 10, borderRadius: 16 }} />
            ))
          : promotions.map((promo, i) => (
              <div key={i} className="card animate-in" style={{
                marginBottom: 10, cursor: 'pointer',
                animationDelay: `${i * 0.08}s`,
              }}
                onClick={() => navigate(`/product/${promo.gtin}`)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <p style={{ fontWeight: 600, fontSize: 14 }}>{promo.name}</p>
                    <p style={{ color: 'var(--muted)', fontSize: 12, marginTop: 2,
                                textTransform: 'capitalize' }}>
                      ● {promo.store} · {promo.promotion_label}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ fontFamily: 'Syne', fontWeight: 700, color: '#4ade80' }}>
                      CHF {promo.promo_price_chf?.toFixed(2)}
                    </p>
                    <p style={{ color: 'var(--muted)', fontSize: 11,
                                textDecoration: 'line-through' }}>
                      CHF {promo.original_price_chf?.toFixed(2)}
                    </p>
                  </div>
                  <span style={{
                    background: '#0d3320', color: '#4ade80',
                    borderRadius: 8, padding: '4px 8px',
                    fontSize: 12, fontWeight: 700, marginLeft: 8,
                  }}>
                    -{promo.discount_pct?.toFixed(0)}%
                  </span>
                </div>
              </div>
            ))
        }
      </div>
    </div>
  )
}
