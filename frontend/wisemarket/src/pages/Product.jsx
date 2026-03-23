import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, ShoppingCart, ExternalLink, Heart } from 'lucide-react'
import { useBasket } from '../hooks/useBasket'
import { api } from '../api/client'
import PriceBar from '../components/PriceBar'

const STORE_URLS = {
  migros: 'https://www.migros.ch',
  coop:   'https://www.coop.ch',
  aldi:   'https://www.aldi.ch',
  lidl:   'https://www.lidl.ch',
  denner: 'https://www.denner.ch',
}

// All ontology tag labels with icons
const ALL_BADGES = {
  // Dietary
  halal:              { label: 'Halal',           icon: '☪️',  color: '#0d3320', text: '#4ade80' },
  vegan:              { label: 'Vegan',            icon: '🌱',  color: '#0d2d1a', text: '#86efac' },
  vegan_likely:       { label: 'Likely Vegan',     icon: '🌿',  color: '#0d2d1a', text: '#6ee7b7' },
  vegetarian:         { label: 'Vegetarian',       icon: '🥦',  color: '#0d2d1a', text: '#bbf7d0' },
  gluten_free:        { label: 'Gluten-Free',      icon: '🌾',  color: '#2d1f00', text: '#fbbf24' },
  lactose_free:       { label: 'Lactose-Free',     icon: '🥛',  color: '#0d1f2d', text: '#7dd3fc' },
  dairy_free:         { label: 'Dairy-Free',       icon: '🚫🥛',color: '#0d1f2d', text: '#93c5fd' },
  nut_free:           { label: 'Nut-Free',         icon: '🥜',  color: '#2d1500', text: '#fb923c' },
  keto:               { label: 'Keto',             icon: '🥑',  color: '#1a2d00', text: '#bef264' },
  low_sugar:          { label: 'Low Sugar',        icon: '🍬',  color: '#1a0d2d', text: '#e879f9' },
  low_fat:            { label: 'Low Fat',          icon: '💧',  color: '#0d1a2d', text: '#7dd3fc' },
  high_protein:       { label: 'High Protein',     icon: '💪',  color: '#1a0d2d', text: '#c4b5fd' },
  high_fiber:         { label: 'High Fibre',       icon: '🌾',  color: '#1a2d00', text: '#86efac' },
  diabetic_friendly:  { label: 'Diabetic-Friendly',icon: '🩺',  color: '#0d1f1a', text: '#6ee7b7' },
  // Labels
  organic:            { label: 'Organic / Bio',    icon: '🌿',  color: '#0d2d1a', text: '#6ee7b7' },
  fairtrade:          { label: 'Fairtrade',        icon: '⚖️',  color: '#1a1a00', text: '#fde68a' },
  sustainable:        { label: 'Sustainable',      icon: '♻️',  color: '#0d2d1a', text: '#6ee7b7' },
  animal_welfare:     { label: 'Animal Welfare',   icon: '🐄',  color: '#1a1000', text: '#fcd34d' },
  regional:           { label: '🇨🇭 Swiss/Regional',icon: '🇨🇭', color: '#2d0d0d', text: '#fca5a5' },
  // Health
  has_vitamins:       { label: 'Rich in Vitamins', icon: '💊',  color: '#0d0d2d', text: '#a5b4fc' },
  has_minerals:       { label: 'Rich in Minerals', icon: '⚡',  color: '#0d0d2d', text: '#c4b5fd' },
  has_antioxidants:   { label: 'Antioxidants',     icon: '🫐',  color: '#1a0d2d', text: '#c4b5fd' },
  has_superfoods:     { label: 'Superfoods',       icon: '✨',  color: '#1a1a00', text: '#fde68a' },
  has_probiotics:     { label: 'Probiotic',        icon: '🦠',  color: '#0d2d1a', text: '#6ee7b7' },
  // Warnings
  has_caffeine:       { label: 'Contains Caffeine',icon: '☕',  color: '#1a0d00', text: '#fdba74' },
  has_palm_oil:       { label: 'Palm Oil',         icon: '🌴',  color: '#1a1000', text: '#fcd34d' },
  has_histamine_risk: { label: 'Histamine Risk',   icon: '⚠️',  color: '#2d0d0d', text: '#fca5a5' },
  has_sulphites:      { label: 'Sulphites',        icon: '⚗️',  color: '#1a1000', text: '#fcd34d' },
  allergen_warning:   { label: 'Allergens',        icon: '⚠️',  color: '#2d0d0d', text: '#f87171' },
  // Lifestyle
  is_sports:          { label: 'Sports Nutrition', icon: '🏋️',  color: '#0d0d2d', text: '#a5b4fc' },
  is_kids_friendly:   { label: 'Kids Friendly',    icon: '👶',  color: '#1a1000', text: '#fde68a' },
  is_bio:             { label: 'Bio',              icon: '🌿',  color: '#0d2d1a', text: '#6ee7b7' },
  is_fairtrade:       { label: 'Fairtrade',        icon: '⚖️',  color: '#1a1a00', text: '#fde68a' },
  is_sustainable:     { label: 'Sustainable',      icon: '♻️',  color: '#0d2d1a', text: '#6ee7b7' },
  is_gluten_free:     { label: 'Gluten-Free',      icon: '🌾',  color: '#2d1f00', text: '#fbbf24' },
  is_lactose_free:    { label: 'Lactose-Free',     icon: '🥛',  color: '#0d1f2d', text: '#7dd3fc' },
  is_low_sugar:       { label: 'Low Sugar',        icon: '🍬',  color: '#1a0d2d', text: '#e879f9' },
  is_high_protein:    { label: 'High Protein',     icon: '💪',  color: '#1a0d2d', text: '#c4b5fd' },
}

function Badge({ tag }) {
  const cfg = ALL_BADGES[tag]
  if (!cfg) return null
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600,
      background: cfg.color, color: cfg.text,
    }}>
      {cfg.icon} {cfg.label}
    </span>
  )
}

export default function Product() {
  const { gtin } = useParams()
  const navigate = useNavigate()
  const [stores, setStores]     = useState([])
  const [selected, setSelected] = useState(0)
  const [prices, setPrices]     = useState(null)
  const [nutrition, setNutrition] = useState(null)
  const [loading, setLoading]   = useState(true)
  const [tab, setTab]           = useState('info')
  const [saved, setSaved]       = useState(false)
  const { addProduct } = useBasket()
  const lang = localStorage.getItem('lang') || 'en'

  const addToBasket = () => {
    addProduct({ gtin, name_en: product?.name_en, name: product?.name_en })
    setSaved(true)
    setTimeout(() => { setSaved(false); navigate('/basket') }, 1000)
  }

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
      <button onClick={() => navigate(-1)} className="btn-ghost" style={{ marginTop: 16, width: 'auto', padding: '10px 24px' }}>Go back</button>
    </div>
  )

  const product = stores[selected] || stores[0]
  const name = product[`name_${lang}`] || product.name_en || 'Unknown'
  const tags = product.ontology_tags || {}
  const allergens = product.allergens || {}

  // Collect all active badges from ontology_tags
  const activeBadges = Object.entries(tags)
    .filter(([k, v]) => v === true && ALL_BADGES[k])
    .map(([k]) => k)

  return (
    <div style={{ paddingBottom: 140 }}>
      {/* Header */}
      <div style={{ padding: '20px 16px 16px', display: 'flex',
                    alignItems: 'flex-start', gap: 12,
                    borderBottom: '1px solid var(--border)',
                    background: 'var(--dark)', position: 'sticky', top: 0, zIndex: 10 }}>
        <button onClick={() => navigate(-1)} style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 10, padding: 8, cursor: 'pointer', flexShrink: 0, marginTop: 2,
        }}>
          <ArrowLeft size={18} />
        </button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ color: 'var(--muted)', fontSize: 11, marginBottom: 2 }}>
            {product.brand} · {product.category}
          </p>
          <h1 style={{ fontFamily: 'Syne', fontSize: 17, fontWeight: 700,
                       lineHeight: 1.3 }}>{name}</h1>
          <p style={{ color: 'var(--muted)', fontSize: 11, marginTop: 2 }}>
            GTIN: {gtin}
          </p>
        </div>
      </div>

      <div style={{ padding: '16px' }}>

        {/* Store selector */}
        {stores.length > 1 && (
          <div style={{ display: 'flex', gap: 8, marginBottom: 16,
                        overflowX: 'auto', scrollbarWidth: 'none' }}>
            {stores.map((s, i) => (
              <button key={s.store} onClick={() => setSelected(i)} style={{
                padding: '6px 14px', borderRadius: 20, whiteSpace: 'nowrap',
                border: `1px solid ${selected === i ? 'var(--red)' : 'var(--border)'}`,
                background: selected === i ? 'rgba(230,57,70,0.1)' : 'var(--surface)',
                color: selected === i ? 'var(--red)' : 'var(--muted)',
                fontSize: 13, fontWeight: selected === i ? 600 : 400,
                cursor: 'pointer', textTransform: 'capitalize',
              }}>
                {s.store}
              </button>
            ))}
          </div>
        )}

        {/* All badges */}
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

        {/* Retailer link */}
        {STORE_URLS[product.store] && (
          <a href={product.source_url || STORE_URLS[product.store]}
            target="_blank" rel="noopener noreferrer"
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '10px 14px', borderRadius: 12, marginBottom: 16,
              background: 'var(--surface)', border: '1px solid var(--border)',
              color: 'var(--muted)', fontSize: 13, textDecoration: 'none',
              transition: 'border-color 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--red)'}
            onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
          >
            <ExternalLink size={14} />
            View on {product.store.charAt(0).toUpperCase() + product.store.slice(1)}
          </a>
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
              <h3 style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 10 }}>Details</h3>
              {[
                ['Category',   product.category],
                ['Sub-category', product.sub_category],
                ['Pack size',  product.pack_size_raw],
                ['Store',      product.store],
                ['Verified',   product.is_verified ? '✅ Yes' : '—'],
                ['Nutri-Score', nutrition?.nutri_score],
                ['NOVA group', nutrition?.nova_group ? `${nutrition.nova_group} / 4` : null],
              ].filter(([,v]) => v).map(([label, val]) => (
                <div key={label} style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: '9px 0', borderBottom: '1px solid var(--border)',
                  fontSize: 13,
                }}>
                  <span style={{ color: 'var(--muted)' }}>{label}</span>
                  <span style={{ fontWeight: 500, textTransform: 'capitalize' }}>{val}</span>
                </div>
              ))}
            </div>

            {/* Full ingredients */}
            {product.ingredients_raw && (
              <div className="card" style={{ marginBottom: 12 }}>
                <h3 style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 10 }}>
                  Ingredients
                </h3>
                <p style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--muted)' }}>
                  {product.ingredients_raw}
                </p>
              </div>
            )}

            {/* All 4 language names */}
            <div className="card">
              <h3 style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 10 }}>
                Product Names
              </h3>
              {[
                ['🇬🇧 EN', product.name_en],
                ['🇩🇪 DE', product.name_de],
                ['🇫🇷 FR', product.name_fr],
                ['🇮🇹 IT', product.name_it],
              ].filter(([,v]) => v).map(([flag, val]) => (
                <div key={flag} style={{
                  display: 'flex', justifyContent: 'space-between', gap: 12,
                  padding: '8px 0', borderBottom: '1px solid var(--border)',
                  fontSize: 13,
                }}>
                  <span style={{ color: 'var(--muted)', flexShrink: 0 }}>{flag}</span>
                  <span style={{ textAlign: 'right' }}>{val}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab: Prices */}
        {tab === 'prices' && (
          <div className="animate-in">
            {prices ? (
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between',
                              marginBottom: 16, alignItems: 'center' }}>
                  <p style={{ color: 'var(--muted)', fontSize: 13 }}>
                    {prices.stores_compared} stores · {prices.snapshot_date}
                  </p>
                  <p style={{ fontSize: 13, color: 'var(--muted)' }}>
                    CHF {prices.cheapest_price_chf?.toFixed(2)} — {prices.most_expensive_price_chf?.toFixed(2)}
                  </p>
                </div>
                <PriceBar prices={prices.prices_chf} />

                {prices.prices_per_100g && Object.keys(prices.prices_per_100g).length > 0 && (
                  <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                    <p style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 10 }}>
                      Per 100g / 100ml
                    </p>
                    {Object.entries(prices.prices_per_100g)
                      .sort(([,a],[,b]) => a - b)
                      .map(([store, p]) => (
                        <div key={store} style={{
                          display: 'flex', justifyContent: 'space-between',
                          fontSize: 13, padding: '6px 0',
                          borderBottom: '1px solid var(--border)',
                        }}>
                          <span style={{ textTransform: 'capitalize', color: 'var(--muted)' }}>
                            {store}
                          </span>
                          <span style={{ fontWeight: 600 }}>CHF {p?.toFixed(4)}</span>
                        </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: 'var(--muted)' }}>
                No price data available
              </div>
            )}
          </div>
        )}

        {/* Tab: Nutrition */}
        {tab === 'nutrition' && (
          <div className="animate-in">
            {nutrition ? (
              <>
                {/* Nutri-Score */}
                {nutrition.nutri_score && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16,
                                marginBottom: 16 }}>
                    <div style={{
                      width: 56, height: 56, borderRadius: '50%', flexShrink: 0,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontFamily: 'Syne', fontWeight: 800, fontSize: 26, color: 'white',
                      background: {A:'#038141',B:'#85BB2F',C:'#FECB02',D:'#EE8100',E:'#E63946'}[nutrition.nutri_score] || '#666',
                    }}>
                      {nutrition.nutri_score}
                    </div>
                    <div>
                      <p style={{ fontWeight: 600 }}>Nutri-Score {nutrition.nutri_score}</p>
                      <p style={{ color: 'var(--muted)', fontSize: 13 }}>
                        NOVA group {nutrition.nova_group} / 4
                      </p>
                    </div>
                  </div>
                )}

                <div className="card" style={{ marginBottom: 12 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>
                    Per 100g / 100ml
                  </h3>
                  {[
                    ['Energy',         nutrition.per_100g?.energy_kcal, 'kcal'],
                    ['Energy (kJ)',     nutrition.per_100g?.energy_kj,   'kJ'],
                    ['Fat',            nutrition.per_100g?.fat,          'g'],
                    ['— Saturated',    nutrition.per_100g?.saturated_fat,'g'],
                    ['Carbohydrates',  nutrition.per_100g?.carbs,        'g'],
                    ['— Sugars',       nutrition.per_100g?.sugars,       'g'],
                    ['Fibre',          nutrition.per_100g?.fibre,        'g'],
                    ['Protein',        nutrition.per_100g?.protein,      'g'],
                    ['Salt',           nutrition.per_100g?.salt,         'g'],
                  ].filter(([,v]) => v != null).map(([label, val, unit]) => (
                    <div key={label} style={{
                      display: 'flex', justifyContent: 'space-between',
                      padding: '9px 0', borderBottom: '1px solid var(--border)',
                      fontSize: 13,
                    }}>
                      <span style={{ color: label.startsWith('—') ? 'var(--muted)' : 'var(--text)',
                                     paddingLeft: label.startsWith('—') ? 12 : 0 }}>
                        {label}
                      </span>
                      <span style={{ fontWeight: 600 }}>{val} {unit}</span>
                    </div>
                  ))}
                </div>

                {/* Per serving */}
                {nutrition.per_serving?.energy_kcal && (
                  <div className="card">
                    <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>
                      Per serving ({nutrition.per_serving?.serving_size_g}g)
                    </h3>
                    {[
                      ['Energy',       nutrition.per_serving?.energy_kcal, 'kcal'],
                      ['Fat',          nutrition.per_serving?.fat,          'g'],
                      ['Carbohydrates',nutrition.per_serving?.carbs,        'g'],
                      ['Sugars',       nutrition.per_serving?.sugars,       'g'],
                      ['Protein',      nutrition.per_serving?.protein,      'g'],
                      ['Salt',         nutrition.per_serving?.salt,         'g'],
                    ].filter(([,v]) => v != null).map(([label, val, unit]) => (
                      <div key={label} style={{
                        display: 'flex', justifyContent: 'space-between',
                        padding: '9px 0', borderBottom: '1px solid var(--border)',
                        fontSize: 13,
                      }}>
                        <span style={{ color: 'var(--muted)' }}>{label}</span>
                        <span style={{ fontWeight: 600 }}>{val} {unit}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: 'var(--muted)' }}>
                No nutrition data available
              </div>
            )}
          </div>
        )}
      </div>

      {/* Add to basket */}
      <div style={{ position: 'fixed', bottom: 70, left: 16, right: 16, zIndex: 10 }}>
        <button onClick={addToBasket} className="btn-primary"
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            background: saved ? '#16a34a' : 'var(--red)',
            transition: 'background 0.3s',
          }}>
          <ShoppingCart size={18} />
          {saved ? '✓ Added to Basket' : 'Add to Basket'}
        </button>
      </div>
    </div>
  )
}
