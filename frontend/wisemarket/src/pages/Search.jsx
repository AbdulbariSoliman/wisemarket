import { useState, useEffect, useRef } from 'react'
import { Search as SearchIcon, X, SlidersHorizontal } from 'lucide-react'
import { api } from '../api/client'
import ProductCard from '../components/ProductCard'

const FILTERS = ['halal','vegan','gluten_free','lactose_free','organic','high_protein','low_sugar']
const FILTER_LABELS = {
  halal: '☪️ Halal', vegan: '🌱 Vegan', gluten_free: '🌾 Gluten-Free',
  lactose_free: '🥛 Lactose-Free', organic: '🌿 Organic',
  high_protein: '💪 Protein', low_sugar: '🍬 Low Sugar',
}

export default function Search() {
  const [query, setQuery]     = useState('')
  const [active, setActive]   = useState({})
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal]     = useState(0)
  const inputRef = useRef()
  const lang = localStorage.getItem('lang') || 'en'

  const doSearch = async (q = query, filters = active) => {
    setLoading(true)
    try {
      const params = { q: q || undefined, lang, limit: 20, ...filters }
      const data = await api.search(params)
      setResults(data.results || [])
      setTotal(data.count || 0)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    doSearch('', {})
  }, [])

  useEffect(() => {
    const t = setTimeout(() => doSearch(), 350)
    return () => clearTimeout(t)
  }, [query, active])

  const toggleFilter = (f) => {
    setActive(prev => ({ ...prev, [f]: prev[f] ? undefined : true }))
  }

  return (
    <div style={{ padding: '24px 16px 100px' }}>
      <h1 style={{ fontFamily: 'Syne', fontSize: 24, fontWeight: 800, marginBottom: 16 }}>
        Search
      </h1>

      {/* Search input */}
      <div style={{ position: 'relative', marginBottom: 14 }}>
        <SearchIcon size={18} color="var(--muted)"
          style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)' }} />
        <input ref={inputRef} value={query} onChange={e => setQuery(e.target.value)}
          placeholder="Search products, brands, ingredients..."
          style={{ paddingLeft: 44, paddingRight: query ? 44 : 16 }} />
        {query && (
          <button onClick={() => setQuery('')} style={{
            position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
            background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)',
          }}>
            <X size={16} />
          </button>
        )}
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4,
                    marginBottom: 20, scrollbarWidth: 'none' }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => toggleFilter(f)} style={{
            whiteSpace: 'nowrap', padding: '6px 14px', borderRadius: 20,
            border: `1px solid ${active[f] ? 'var(--red)' : 'var(--border)'}`,
            background: active[f] ? 'rgba(230,57,70,0.12)' : 'var(--surface)',
            color: active[f] ? 'var(--red)' : 'var(--muted)',
            fontSize: 12, fontWeight: active[f] ? 600 : 400, cursor: 'pointer',
            transition: 'all 0.15s',
          }}>
            {FILTER_LABELS[f]}
          </button>
        ))}
      </div>

      {/* Results count */}
      {!loading && (
        <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 14 }}>
          {total} product{total !== 1 ? 's' : ''} found
        </p>
      )}

      {/* Results */}
      {loading
        ? [1,2,3,4,5].map(i => (
            <div key={i} className="skeleton" style={{ height: 88, marginBottom: 10, borderRadius: 16 }} />
          ))
        : results.map((p, i) => (
            <div key={`${p.gtin}-${p.store}`} style={{ animationDelay: `${i * 0.04}s` }}>
              <ProductCard product={p} />
            </div>
          ))
      }

      {!loading && results.length === 0 && (
        <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--muted)' }}>
          <p style={{ fontSize: 40, marginBottom: 12 }}>🔍</p>
          <p style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>No results found</p>
          <p style={{ fontSize: 14 }}>Try a different search or remove filters</p>
        </div>
      )}
    </div>
  )
}
