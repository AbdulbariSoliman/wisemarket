import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, ShoppingCart, ExternalLink } from 'lucide-react'
import { api } from '../api/client'
import PriceBar from '../components/PriceBar'
import { useBasket } from '../hooks/useBasket'

const STORE_URLS = {
  migros: 'https://www.migros.ch',
  coop:   'https://www.coop.ch',
  aldi:   'https://www.aldi.ch',
  lidl:   'https://www.lidl.ch',
}

const ALL_BADGES = {
  halal:           { label: 'Halal',            icon: '☪️',  bg: '#0d3320', color: '#4ade80' },
  vegan:           { label: 'Vegan',             icon: '🌱',  bg: '#0d2d1a', color: '#86efac' },
  vegan_likely:    { label: 'Likely Vegan',      icon: '🌿',  bg: '#0d2d1a', color: '#6ee7b7' },
  vegetarian:      { label: 'Vegetarian',        icon: '🥦',  bg: '#0d2d1a', color: '#bbf7d0' },
  gluten_free:     { label: 'Gluten-Free',       icon: '🌾',  bg: '#2d1f00', color: '#fbbf24' },
  lactose_free:    { label: 'Lactose-Free',      icon: '🥛',  bg: '#0d1f2d', color: '#7dd3fc' },
  dairy_free:      { label: 'Dairy-Free',        icon: '🚫',  bg: '#0d1f2d', color: '#93c5fd' },
  nut_free:        { label: 'Nut-Free',          icon: '🥜',  bg: '#2d1500', color: '#fb923c' },
  organic:         { label: 'Organic / Bio',     icon: '🌿',  bg: '#0d2d1a', color: '#6ee7b7' },
  is_bio:          { label: 'Bio',               icon: '🌿',  bg: '#0d2d1a', color: '#6ee7b7' },
  regional:        { label: 'Aus der Region',    icon: '🇨🇭',  bg: '#2d0d0d', color: '#fca5a5' },
  is_regional:     { label: 'Regional',          icon: '🇨🇭',  bg: '#2d0d0d', color: '#fca5a5' },
  fairtrade:       { label: 'Fairtrade',         icon: '⚖️',  bg: '#1a1a00', color: '#fde68a' },
  high_protein:    { label: 'High Protein',      icon: '💪',  bg: '#1a0d2d', color: '#c4b5fd' },
  low_sugar:       { label: 'Low Sugar',         icon: '🍬',  bg: '#1a0d2d', color: '#e879f9' },
  low_fat:         { label: 'Low Fat',           icon: '💧',  bg: '#0d1a2d', color: '#7dd3fc' },
  high_fiber:      { label: 'High Fibre',        icon: '🌾',  bg: '#1a2d00', color: '#86efac' },
  keto:            { label: 'Keto',              icon: '🥑',  bg: '#1a2d00', color: '#bef264' },
  has_caffeine:    { label: 'Contains Caffeine', icon: '☕',  bg: '#1a0d00', color: '#fdba74' },
  has_palm_oil:    { label: 'Palm Oil',          icon: '🌴',  bg: '#1a1000', color: '#fcd34d' },
  allergen_warning:{ label: 'Allergens',         icon: '⚠️',  bg: '#2d0d0d', color: '#f87171' },
  is_kids_friendly:{ label: 'Kids Friendly',     icon: '👶',  bg: '#1a1000', color: '#fde68a' },
  is_sports:       { label: 'Sports',            icon: '🏋️',  bg: '#0d0d2d', color: '#a5b4fc' },
}

function Badge({ tag }) {
  const cfg = ALL_BADGES[tag]
  if (!cfg) return null
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600,
      background: cfg.bg, color: cfg.color,
    }}>
      {cfg.icon} {cfg.label}
    </span>
  )
}

function NutrRow({ label, value, unit, indent }) {
  if (value == null) return null
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between',
      padding: '9px 0', borderBottom: '1px solid var(--border)',
      fontSize: 13,
    }}>
      <span style={{ color: indent ? 'var(--muted)' : 'var(--text)',
                     paddingLeft: indent ? 12 : 0 }}>{label}</span>
      <span style={{ fontWeight: 600 }}>{value} {unit}</span>
    </div>
  )
}

export default function Product() {
  const { gtin } = useParams()
  const navigate = useNavigate()
  const { addProduct } = useBasket()
  const [stores, setStores]   = useState([])
  const [prices, setPrices]   = useState(null)
  const [nutrition, setNutrition] = useState(null)
  const [loading, setLoading] = useState(true)
  const [added, setAdded]     = useState(false)
  const [selected, setSelected] = useState(0)
  const lang = localStorage.getItem('lang') || 'en'

  useEffect(() => {
    Promise.all([
      api.product(gtin, { lang }),
      api.compare(gtin).catch(() => null),
      api.nutrition(gtin).catch(() => null),
    ]).then(([p, c, n]) => {
      setStores(p.stores || [])
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

  if (!stores.length) return (
    <div style={{ padding: 40, textAlign: 'center', color: 'var(--muted)' }}>
      <p style={{ fontSize: 40 }}>😕</p>
      <p style={{ marginTop: 12 }}>Product not found</p>
      <button onClick={() => navigate(-1)} className="btn-ghost"
        style={{ marginTop: 16, width: 'auto', padding: '10px 24px' }}>Go back</button>
    </div>
  )

  const product = stores[selected] || stores[0]
  const name = product[`name_${lang}`] || product.name_en || product.name_de || product.name || 'Unknown'
  const tags = product.ontology_tags || {}
  const allergens = product.allergens || {}
  const activeBadges = Object.entries(tags).filter(([k,v]) => v === true && ALL_BADGES[k]).map(([k]) => k)

  const handleAdd = () => {
    addProduct({ gtin, name_en: name, name })
    setAdded(true)
    setTimeout(() => { setAdded(false); navigate('/basket') }, 800)
  }

  // Build direct product URL
  const getProductUrl = () => {
    if (product.source_url) return product.source_url
    const store = product.store
    // Migros: use source_url from DB or search fallback
    if (store === 'migros') {
      return `https://www.migros.ch/de/search?query=${encodeURIComponent(name)}`
    }
    if (store === 'coop') {
      return `https://www.coop.ch/de/search?q=${encodeURIComponent(name)}`
    }
    if (store === 'aldi') return `https://www.aldi.ch/de/produkte.html?q=${encodeURIComponent(name)}`
    if (store === 'lidl') return `https://www.lidl.ch/de/suche?query=${encodeURIComponent(name)}`
    if (store === 'open_food_facts') return `https://world.openfoodfacts.org/product/${gtin}`
    return STORE_URLS[store] || null
  }

  return (
    <div style={{ paddingBottom: 120 }}>
      {/* Sticky header */}
      <div style={{
        padding: '16px 16px 12px', display: 'flex', alignItems: 'flex-start', gap: 12,
        borderBottom: '1px solid var(--border)', background: 'var(--dark)',
        position: 'sticky', top: 0, zIndex: 10,
      }}>
        <button onClick={() => navigate(-1)} style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 10, padding: 8, cursor: 'pointer', flexShrink: 0,
        }}>
          <ArrowLeft size={18} />
        </button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ color: 'var(--muted)', fontSize: 11, marginBottom: 2 }}>
            {product.brand} · {product.category} · {gtin}
          </p>
          <h1 style={{ fontFamily: 'Syne', fontSize: 16, fontWeight: 700, lineHeight: 1.3 }}>
            {name}
          </h1>
        </div>
      </div>

      <div style={{ padding: '16px 16px 0' }}>

        {/* Store selector */}
        {stores.length > 1 && (
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, overflowX: 'auto', scrollbarWidth: 'none' }}>
            {stores.map((s, i) => (
              <button key={s.store} onClick={() => setSelected(i)} style={{
                padding: '6px 14px', borderRadius: 20, whiteSpace: 'nowrap', cursor: 'pointer',
                border: `1px solid ${selected === i ? 'var(--red)' : 'var(--border)'}`,
                background: selected === i ? 'rgba(230,57,70,0.1)' : 'var(--surface)',
                color: selected === i ? 'var(--red)' : 'var(--muted)',
                fontSize: 13, fontWeight: selected === i ? 600 : 400,
                textTransform: 'capitalize', transition: 'all 0.15s',
              }}>
                {s.store}
              </button>
            ))}
          </div>
        )}

        {/* Badges */}
        {activeBadges.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
            {activeBadges.map(b => <Badge key={b} tag={b} />)}
          </div>
        )}

        {/* Allergen warning */}
        {allergens.contains?.length > 0 && (
          <div style={{
            background: 'rgba(230,57,70,0.08)', border: '1px solid rgba(230,57,70,0.3)',
            borderRadius: 12, padding: '10px 14px', marginBottom: 16,
          }}>
            <p style={{ fontSize: 13, color: '#fca5a5' }}>
              ⚠️ <strong>Contains:</strong> {allergens.contains.join(', ')}
            </p>
            {allergens.may_contain?.length > 0 && (
              <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
                May contain: {allergens.may_contain.join(', ')}
              </p>
            )}
          </div>
        )}

        {/* Retailer link — direct product URL */}
        {getProductUrl() && (
          <a href={getProductUrl()} target="_blank" rel="noopener noreferrer" style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 14px', borderRadius: 12, marginBottom: 20,
            background: 'var(--surface)', border: '1px solid var(--border)',
            color: 'var(--muted)', fontSize: 13, textDecoration: 'none',
            transition: 'border-color 0.15s',
          }}
            onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--red)'}
            onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
          >
            <ExternalLink size={14} />
            View product on {product.store?.charAt(0).toUpperCase() + product.store?.slice(1)}
          </a>
        )}

        {/* ── SECTION 1: PRICE COMPARISON ── */}
        {prices && (
          <div className="card" style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--muted)', marginBottom: 12 }}>
              Price comparison · {prices.stores_compared} stores
            </p>
            <PriceBar prices={prices.prices_chf} />
            {prices.prices_per_100g && Object.keys(prices.prices_per_100g).length > 0 && (
              <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
                <p style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 8 }}>Per 100g / 100ml</p>
                {Object.entries(prices.prices_per_100g).sort(([,a],[,b]) => a-b).map(([store, p]) => (
                  <div key={store} style={{
                    display: 'flex', justifyContent: 'space-between',
                    fontSize: 12, padding: '4px 0', color: 'var(--muted)',
                  }}>
                    <span style={{ textTransform: 'capitalize' }}>{store}</span>
                    <span style={{ fontWeight: 600, color: 'var(--text)' }}>CHF {p?.toFixed(4)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── SECTION 2: NUTRITION ── */}
        {nutrition && (
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 14 }}>
              {nutrition.nutri_score && (
                <div style={{
                  width: 48, height: 48, borderRadius: '50%', flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontFamily: 'Syne', fontWeight: 800, fontSize: 22, color: 'white',
                  background: {A:'#038141',B:'#85BB2F',C:'#FECB02',D:'#EE8100',E:'#E63946'}[nutrition.nutri_score] || '#666',
                }}>
                  {nutrition.nutri_score}
                </div>
              )}
              <div>
                <p style={{ fontWeight: 600, fontSize: 14 }}>Nutrition · per 100g</p>
                {nutrition.nova_group && (
                  <p style={{ color: 'var(--muted)', fontSize: 12, marginTop: 2 }}>
                    NOVA group {nutrition.nova_group} / 4
                  </p>
                )}
              </div>
            </div>
            <NutrRow label="Energy"       value={nutrition.per_100g?.energy_kcal} unit="kcal" />
            <NutrRow label="Fat"          value={nutrition.per_100g?.fat}          unit="g" />
            <NutrRow label="— Saturated"  value={nutrition.per_100g?.saturated_fat} unit="g" indent />
            <NutrRow label="Carbohydrates"value={nutrition.per_100g?.carbs}         unit="g" />
            <NutrRow label="— Sugars"     value={nutrition.per_100g?.sugars}        unit="g" indent />
            <NutrRow label="Fibre"        value={nutrition.per_100g?.fibre}         unit="g" />
            <NutrRow label="Protein"      value={nutrition.per_100g?.protein}       unit="g" />
            <NutrRow label="Salt"         value={nutrition.per_100g?.salt}          unit="g" />
          </div>
        )}

        {/* ── SECTION 3: PRODUCT INFO ── */}
        <div className="card" style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--muted)', marginBottom: 12 }}>
            Product info
          </p>
          {[
            ['Category',   product.category],
            ['Pack size',  product.pack_size_raw],
            ['Brand',      product.brand],
            ['GTIN',       gtin],
            ['Store',      product.store],
          ].filter(([,v]) => v).map(([label, val]) => (
            <div key={label} style={{
              display: 'flex', justifyContent: 'space-between',
              padding: '9px 0', borderBottom: '1px solid var(--border)', fontSize: 13,
            }}>
              <span style={{ color: 'var(--muted)' }}>{label}</span>
              <span style={{ fontWeight: 500, textTransform: 'capitalize' }}>{val}</span>
            </div>
          ))}
        </div>

        {/* Ingredients */}
        {product.ingredients_raw && (
          <div className="card" style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--muted)', marginBottom: 10 }}>
              Ingredients
            </p>
            <p style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--muted)' }}>
              {product.ingredients_raw}
            </p>
          </div>
        )}

        {/* All 4 language names */}
        <div className="card" style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--muted)', marginBottom: 10 }}>
            Product names
          </p>
          {[
            ['🇬🇧 EN', product.name_en],
            ['🇩🇪 DE', product.name_de],
            ['🇫🇷 FR', product.name_fr],
            ['🇮🇹 IT', product.name_it],
          ].filter(([,v]) => v).map(([flag, val]) => (
            <div key={flag} style={{
              display: 'flex', justifyContent: 'space-between', gap: 12,
              padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 13,
            }}>
              <span style={{ color: 'var(--muted)', flexShrink: 0 }}>{flag}</span>
              <span style={{ textAlign: 'right' }}>{val}</span>
            </div>
          ))}
        </div>

      </div>

      {/* Add to basket */}
      <div style={{ position: 'fixed', bottom: 70, left: 16, right: 16, zIndex: 10 }}>
        <button onClick={handleAdd} className="btn-primary" style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          background: added ? '#16a34a' : 'var(--red)', transition: 'background 0.3s',
        }}>
          <ShoppingCart size={18} />
          {added ? '✓ Added!' : 'Add to Basket'}
        </button>
      </div>
    </div>
  )
}
