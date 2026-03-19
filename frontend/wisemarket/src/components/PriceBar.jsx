const STORE_COLORS = {
  migros: '#FF6600', coop: '#E2001A',
  aldi: '#00539F', lidl: '#0050AA', denner: '#C8102E'
}

export default function PriceBar({ prices, cheapest }) {
  if (!prices || Object.keys(prices).length === 0) return null
  const max = Math.max(...Object.values(prices))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {Object.entries(prices)
        .sort(([,a],[,b]) => a - b)
        .map(([store, price]) => {
          const pct = (price / max) * 100
          const isCheapest = store === cheapest
          const color = STORE_COLORS[store] || '#6B6B74'
          return (
            <div key={store}>
              <div style={{ display: 'flex', justifyContent: 'space-between',
                            marginBottom: 4, alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ color, fontSize: 12 }}>●</span>
                  <span style={{ fontSize: 13, fontWeight: isCheapest ? 600 : 400,
                                 textTransform: 'capitalize' }}>{store}</span>
                  {isCheapest && (
                    <span style={{ background: '#0d3320', color: '#4ade80',
                                   fontSize: 10, padding: '1px 6px',
                                   borderRadius: 10, fontWeight: 600 }}>Best</span>
                  )}
                </div>
                <span style={{ fontFamily: 'Syne', fontWeight: 700,
                               color: isCheapest ? '#4ade80' : 'var(--text)' }}>
                  CHF {price.toFixed(2)}
                </span>
              </div>
              <div style={{ background: 'var(--border)', borderRadius: 4, height: 4 }}>
                <div style={{
                  width: `${pct}%`, height: '100%',
                  background: isCheapest ? '#4ade80' : color,
                  borderRadius: 4, transition: 'width 0.6s ease',
                  opacity: isCheapest ? 1 : 0.5,
                }} />
              </div>
            </div>
          )
        })}
    </div>
  )
}
