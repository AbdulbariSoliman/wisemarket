import { useNavigate } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { getCarbonScore } from '../data/seasonal'

const BADGE_KEYS = [
  'halal','vegan','vegan_likely','vegetarian','gluten_free',
  'organic','high_protein','lactose_free','dairy_free','nut_free'
]

const STORE_COLORS = {
  migros: '#FF6600', coop: '#E2001A',
  aldi: '#00539F', lidl: '#0050AA', denner: '#C8102E'
}

export default function ProductCard({ product, price, showStore = true }) {
  const navigate = useNavigate()
  const name = product.name || product.name_en || 'Unknown'
  const tags = product.ontology_tags || {}
  const badges = BADGE_KEYS.filter(k => tags[k])
  const storeColor = STORE_COLORS[product.store] || '#6B6B74'

  return (
    <div className="card animate-in" onClick={() => navigate(`/product/${product.gtin}`)}
      style={{ cursor: 'pointer', display: 'flex', gap: 12, alignItems: 'flex-start',
               transition: 'border-color 0.15s', marginBottom: 10 }}
      onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--red)'}
      onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
    >
      {/* Image placeholder */}
      <div style={{
        width: 56, height: 56, borderRadius: 10, flexShrink: 0,
        background: 'var(--border)', display: 'flex', alignItems: 'center',
        justifyContent: 'center', fontSize: 24,
      }}>
        {tags.vegan ? '🌱' : tags.halal ? '☪️' : tags.gluten_free ? '🌾' : '🛒'}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <p style={{ fontWeight: 600, fontSize: 14, lineHeight: 1.3,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        maxWidth: '200px' }}>{name}</p>
            <p style={{ color: 'var(--muted)', fontSize: 12, marginTop: 2 }}>
              {product.brand}
              {showStore && product.store && (
                <span style={{ color: storeColor, marginLeft: 6 }}>
                  ● {product.store}
                </span>
              )}
            </p>
          </div>
          {price && (
            <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 8 }}>
              <p style={{ fontFamily: 'Syne', fontWeight: 700, fontSize: 16,
                          color: 'var(--text)' }}>CHF {price}</p>
              {product.price_per_100g && (
                <p style={{ color: 'var(--muted)', fontSize: 10 }}>
                  {product.price_per_100g}/100g
                </p>
              )}
            </div>
          )}
        </div>

        {/* Carbon score */}
        {(() => {
          const carbon = getCarbonScore(product.name || product.name_en || product.name_de, product.category)
          if (!carbon) return null
          const colors = { A:'#038141', B:'#85BB2F', C:'#FECB02', D:'#EE8100', E:'#E63946' }
          return (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 3,
              marginTop: 6, fontSize: 10, fontWeight: 700,
              color: colors[carbon.score] || '#888',
            }}>
              🌍 CO₂ {carbon.score}
            </span>
          )
        })()}

        {badges.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
            {badges.slice(0, 4).map(b => (
              <span key={b} className={`badge badge-${b}`}>
                {b === 'halal' ? '☪️' : b === 'vegan' ? '🌱' : b === 'gluten_free' ? 'GF' :
                 b === 'organic' ? '🌿' : b === 'high_protein' ? '💪' : b === 'vegetarian' ? '🥦' :
                 b === 'lactose_free' ? 'LF' : b === 'nut_free' ? 'NF' : b}
              </span>
            ))}
          </div>
        )}
      </div>

      <ChevronRight size={16} color="var(--muted)" style={{ flexShrink: 0, marginTop: 4 }} />
    </div>
  )
}
