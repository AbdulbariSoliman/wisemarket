import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, ShoppingCart, Heart, Share2 } from 'lucide-react'
import { api } from '../api/client'
import PriceBar from '../components/PriceBar'

const BADGE_KEYS = ['halal','vegan','vegetarian','gluten_free','organic','high_protein','lactose_free','dairy_free','nut_free','low_sugar']
const BADGE_LABELS = {
  halal:'☪️ Halal', vegan:'🌱 Vegan', vegetarian:'🥦 Vegetarian',
  gluten_free:'🌾 Gluten-Free', organic:'🌿 Organic',
  high_protein:'💪 High Protein', lactose_free:'🥛 Lactose-Free',
  dairy_free:'DF Dairy-Free', nut_free:'NF Nut-Free', low_sugar:'🍬 Low Sugar',
}

export default function Product() {
  const { gtin } = useParams()
  const navigate = useNavigate()
  const [product, setProduct]   = useState(null)
  const [prices, setPrices]     = useState(null)
  const [nutrition, setNutrition] = useState(null)
  const [loading, setLoading]   = useState(true)
  const [tab, setTab]           = useState('info')
  const lang = localStorage.getItem('lang') || 'en'

  useEffect(() => {
    Promise.all([
      api.product(gtin, { lang }),
      api.compare(gtin),
      api.nutrition(gtin).catch(() => null),
    ]).then(([p, c, n]) => {
      setProduct(p.stores?.[0] || null)
      setPrices(c)
      setNutrition(n)
    }).finally(() => setLoading(false))
  }, [gtin])

  if (loading) return (
    <div style={{ padding: 20 }}>
      {[1,2,3].map(i => (
        <div key={i} className="skeleton" style={{ height: 80, borderRadius: 16, marginBottom: 12 }} />
      ))}
    </div>
  )

  if (!product) return (
    <div style={{ padding: 40, textAlign: 'center', color: 'var(--muted)' }}>
      <p style={{ fontSize: 40 }}>😕</p>
      <p style={{ marginTop: 12 }}>Product not found</p>
    </div>
  )

  const tags = product.ontology_tags || {}
  const badges = BADGE_KEYS.filter(k => tags[k])
  const name = product[`name_${lang}`] || product.name_en || 'Unknown'

  return (
    <div style={{ paddingBottom: 100 }}>
      {/* Header */}
      <div style={{ padding: '20px 16px', display: 'flex',
                    alignItems: 'center', gap: 12, borderBottom: '1px solid var(--border)' }}>
        <button onClick={() => navigate(-1)} style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 10, padding: 8, cursor: 'pointer',
        }}>
          <ArrowLeft size={18} />
        </button>
        <div style={{ flex: 1 }}>
          <p style={{ color: 'var(--muted)', fontSize: 12 }}>{product.brand}</p>
          <h1 style={{ fontFamily: 'Syne', fontSize: 18, fontWeight: 700,
                       lineHeight: 1.2 }}>{name}</h1>
        </div>
        <button style={{ background: 'none', border: 'none', cursor: 'pointer',
                         color: 'var(--muted)', padding: 8 }}>
          <Heart size={20} />
        </button>
      </div>

      <div style={{ padding: '16px' }}>
        {/* Badges */}
        {badges.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 20 }}>
            {badges.map(b => (
              <span key={b} className={`badge badge-${b}`} style={{ fontSize: 12, padding: '5px 12px' }}>
                {BADGE_LABELS[b]}
              </span>
            ))}
          </div>
        )}

        {/* Allergens warning */}
        {product.allergens?.contains?.length > 0 && (
          <div style={{
            background: 'rgba(230,57,70,0.08)', border: '1px solid rgba(230,57,70,0.3)',
            borderRadius: 12, padding: '10px 14px', marginBottom: 16,
            display: 'flex', gap: 8, alignItems: 'center',
          }}>
            <span style={{ fontSize: 16 }}>⚠️</span>
            <p style={{ fontSize: 13, color: '#fca5a5' }}>
              Contains: {product.allergens.contains.join(', ')}
            </p>
          </div>
        )}

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 20,
                      background: 'var(--surface)', borderRadius: 12, padding: 4 }}>
          {['info','prices','nutrition'].map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              flex: 1, padding: '8px 0', border: 'none', borderRadius: 8,
              background: tab === t ? 'var(--dark)' : 'transparent',
              color: tab === t ? 'var(--text)' : 'var(--muted)',
              fontWeight: tab === t ? 600 : 400, fontSize: 13,
              cursor: 'pointer', transition: 'all 0.15s', textTransform: 'capitalize',
            }}>
              {t}
            </button>
          ))}
        </div>

        {/* Tab: Info */}
        {tab === 'info' && (
          <div className="animate-in">
            <div className="card" style={{ marginBottom: 12 }}>
              <h3 style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 8 }}>Details</h3>
              {[
                ['Category', product.category],
                ['Pack size', product.pack_size_raw],
                ['Nutri-Score', product.nutrition?.nutri_score],
                ['NOVA group', product.nutrition?.nova_group],
              ].filter(([,v]) => v).map(([label, val]) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between',
                                          padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ color: 'var(--muted)', fontSize: 13 }}>{label}</span>
                  <span style={{ fontSize: 13, fontWeight: 500 }}>{val}</span>
                </div>
              ))}
            </div>
            {product.ingredients_raw && (
              <div className="card">
                <h3 style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 8 }}>Ingredients</h3>
                <p style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--muted)' }}>
                  {product.ingredients_raw}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Tab: Prices */}
        {tab === 'prices' && (
          <div className="animate-in">
            {prices ? (
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between',
                              marginBottom: 16, alignItems: 'center' }}>
                  <div>
                    <p style={{ color: 'var(--muted)', fontSize: 12 }}>Cheapest</p>
                    <p style={{ fontFamily: 'Syne', fontSize: 22, fontWeight: 800,
                                color: '#4ade80' }}>
                      CHF {prices.cheapest_price_chf?.toFixed(2)}
                    </p>
                    <p style={{ color: 'var(--muted)', fontSize: 12 }}>
                      at {prices.cheapest_store}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ color: 'var(--muted)', fontSize: 12 }}>Price spread</p>
                    <p style={{ fontFamily: 'Syne', fontSize: 18, fontWeight: 700 }}>
                      {prices.price_spread_pct?.toFixed(1)}%
                    </p>
                    <p style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {prices.stores_compared} stores
                    </p>
                  </div>
                </div>
                <PriceBar prices={prices.prices_chf} cheapest={prices.cheapest_store} />
                {prices.prices_per_100g && Object.keys(prices.prices_per_100g).length > 0 && (
                  <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                    <p style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 8 }}>Per 100g/ml</p>
                    {Object.entries(prices.prices_per_100g).map(([store, p]) => (
                      <div key={store} style={{ display: 'flex', justifyContent: 'space-between',
                                                fontSize: 13, padding: '4px 0' }}>
                        <span style={{ textTransform: 'capitalize' }}>{store}</span>
                        <span style={{ fontWeight: 600 }}>CHF {p?.toFixed(3)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p style={{ color: 'var(--muted)', fontSize: 14, textAlign: 'center', padding: 40 }}>
                No price data available
              </p>
            )}
          </div>
        )}

        {/* Tab: Nutrition */}
        {tab === 'nutrition' && (
          <div className="animate-in">
            {nutrition ? (
              <div className="card">
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 14 }}>Per 100g / 100ml</h3>
                {[
                  ['Energy',       `${nutrition.per_100g?.energy_kcal} kcal`],
                  ['Fat',          `${nutrition.per_100g?.fat}g`],
                  ['Saturated fat',`${nutrition.per_100g?.saturated_fat}g`],
                  ['Carbohydrates',`${nutrition.per_100g?.carbs}g`],
                  ['Sugars',       `${nutrition.per_100g?.sugars}g`],
                  ['Fibre',        `${nutrition.per_100g?.fibre}g`],
                  ['Protein',      `${nutrition.per_100g?.protein}g`],
                  ['Salt',         `${nutrition.per_100g?.salt}g`],
                ].filter(([,v]) => v && v !== 'undefinedg' && v !== 'undefinedkcal').map(([label, val]) => (
                  <div key={label} style={{ display: 'flex', justifyContent: 'space-between',
                                            padding: '10px 0', borderBottom: '1px solid var(--border)',
                                            fontSize: 14 }}>
                    <span style={{ color: 'var(--muted)' }}>{label}</span>
                    <span style={{ fontWeight: 600 }}>{val}</span>
                  </div>
                ))}
                {nutrition.nutri_score && (
                  <div style={{ marginTop: 16, textAlign: 'center' }}>
                    <span style={{
                      display: 'inline-block',
                      background: {'A':'#038141','B':'#85BB2F','C':'#FECB02','D':'#EE8100','E':'#E63946'}[nutrition.nutri_score] || '#666',
                      color: 'white', fontFamily: 'Syne', fontWeight: 800,
                      fontSize: 24, width: 48, height: 48, borderRadius: '50%',
                      lineHeight: '48px',
                    }}>
                      {nutrition.nutri_score}
                    </span>
                    <p style={{ color: 'var(--muted)', fontSize: 12, marginTop: 6 }}>Nutri-Score</p>
                  </div>
                )}
              </div>
            ) : (
              <p style={{ color: 'var(--muted)', fontSize: 14, textAlign: 'center', padding: 40 }}>
                No nutrition data available
              </p>
            )}
          </div>
        )}
      </div>

      {/* Add to basket */}
      <div style={{ position: 'fixed', bottom: 70, left: 16, right: 16 }}>
        <button className="btn-primary" style={{ display: 'flex', alignItems: 'center',
                                                  justifyContent: 'center', gap: 8 }}>
          <ShoppingCart size={18} /> Add to Basket
        </button>
      </div>
    </div>
  )
}
