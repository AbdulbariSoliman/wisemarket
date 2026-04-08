import { useState, useEffect } from 'react'
import { ArrowLeft, Navigation, Clock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const STORE_COLORS = {
  migros:'#FF6600', coop:'#E2001A', aldi:'#00539F', lidl:'#0050AA',
  denner:'#C8102E', manor:'#1A1A2E', volg:'#2E7D32', spar:'#007A33',
}
const STORE_ICONS = {
  migros:'🟠', coop:'🔴', aldi:'🔵', lidl:'🔵',
  denner:'🟤', manor:'⚫', volg:'🟢', spar:'🟢', other:'🛒',
}
const BRANDS = ['Migros','Coop','Aldi','Lidl','Denner','Manor','Volg','Spar']

function dist(lat1,lon1,lat2,lon2) {
  const R=6371000, dLat=(lat2-lat1)*Math.PI/180, dLon=(lon2-lon1)*Math.PI/180
  const a=Math.sin(dLat/2)**2+Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2
  return Math.round(R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a)))
}

export default function StoreMap() {
  const navigate = useNavigate()
  const [stores, setStores]   = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const [selected, setSelected] = useState(null)

  const find = () => {
    setLoading(true)
    setError('')
    navigator.geolocation.getCurrentPosition(
      async pos => {
        const {latitude:lat, longitude:lon} = pos.coords
        const q = `[out:json][timeout:15];(node["shop"="supermarket"](around:2000,${lat},${lon});node["shop"="discount"](around:2000,${lat},${lon}););out body;`
        try {
          const r = await fetch('https://overpass-api.de/api/interpreter', {method:'POST', body:q})
          const d = await r.json()
          const results = (d.elements||[])
            .filter(e => BRANDS.some(b => (e.tags?.name||'').toLowerCase().includes(b.toLowerCase())))
            .map(e => {
              const name = e.tags?.name||'Store'
              const brand = (BRANDS.find(b => name.toLowerCase().includes(b.toLowerCase()))||'other').toLowerCase()
              return {
                id: e.id, name, brand,
                lat: e.lat, lon: e.lon,
                distance: dist(lat,lon,e.lat,e.lon),
                hours: e.tags?.opening_hours||null,
                address: [e.tags?.['addr:street'],e.tags?.['addr:housenumber'],e.tags?.['addr:city']].filter(Boolean).join(' '),
              }
            })
            .sort((a,b)=>a.distance-b.distance)
            .slice(0,15)
          setStores(results)
        } catch(e) { setError('Could not load nearby stores.') }
        setLoading(false)
      },
      () => { setError('Location access denied.'); setLoading(false) },
      { timeout:10000 }
    )
  }

  useEffect(() => { find() }, [])

  const fmt = m => m < 1000 ? `${m}m` : `${(m/1000).toFixed(1)}km`

  return (
    <div style={{ paddingBottom: 90 }}>
      <div style={{ padding:'16px 16px 12px', display:'flex', alignItems:'center',
                    gap:12, borderBottom:'1px solid var(--border)',
                    background:'var(--dark)', position:'sticky', top:0, zIndex:10 }}>
        <button onClick={() => navigate(-1)} style={{
          background:'var(--surface)', border:'1px solid var(--border)',
          borderRadius:10, padding:8, cursor:'pointer' }}>
          <ArrowLeft size={18}/>
        </button>
        <div style={{ flex:1 }}>
          <h1 style={{ fontFamily:'Syne', fontSize:18, fontWeight:700, margin:0 }}>Nearby Stores</h1>
          {stores.length > 0 && <p style={{ fontSize:11, color:'var(--muted)', margin:0 }}>{stores.length} stores found</p>}
        </div>
        <button onClick={find} style={{
          background:'var(--red)', border:'none', borderRadius:10,
          padding:'8px 14px', color:'white', fontSize:13, cursor:'pointer',
          display:'flex', alignItems:'center', gap:6 }}>
          <Navigation size={14}/> Refresh
        </button>
      </div>

      <div style={{ padding:16 }}>
        {loading && [1,2,3,4].map(i => (
          <div key={i} className="skeleton" style={{ height:80, borderRadius:14, marginBottom:10 }}/>
        ))}

        {error && (
          <div style={{ background:'rgba(230,57,70,0.08)', border:'1px solid rgba(230,57,70,0.3)',
                        borderRadius:12, padding:16, textAlign:'center' }}>
            <p style={{ color:'#fca5a5', fontSize:14, marginBottom:12 }}>{error}</p>
            <button onClick={find} className="btn-primary" style={{ width:'auto', padding:'10px 24px' }}>Try again</button>
          </div>
        )}

        {stores.map((s,i) => {
          const color = STORE_COLORS[s.brand] || '#6B6B74'
          return (
            <div key={s.id} className="card animate-in" style={{
              marginBottom:10, cursor:'pointer',
              animationDelay:`${i*0.05}s`,
              border: selected===s.id ? `1px solid ${color}` : '1px solid var(--border)',
            }} onClick={() => setSelected(selected===s.id ? null : s.id)}>
              <div style={{ display:'flex', alignItems:'center', gap:12 }}>
                <div style={{
                  width:44, height:44, borderRadius:12, flexShrink:0,
                  background:`${color}22`,
                  display:'flex', alignItems:'center', justifyContent:'center', fontSize:20,
                }}>
                  {STORE_ICONS[s.brand]||'🛒'}
                </div>
                <div style={{ flex:1, minWidth:0 }}>
                  <p style={{ margin:0, fontWeight:600, fontSize:14 }}>{s.name}</p>
                  <p style={{ margin:'2px 0 0', fontSize:12, color }}>● {s.brand} · {fmt(s.distance)}</p>
                  {s.address && <p style={{ margin:'2px 0 0', fontSize:11, color:'var(--muted)',
                    overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{s.address}</p>}
                </div>
                <span style={{ fontSize:13, color:'var(--muted)', flexShrink:0 }}>{fmt(s.distance)}</span>
              </div>

              {selected===s.id && (
                <div style={{ marginTop:12, paddingTop:12, borderTop:'1px solid var(--border)' }}
                  className="animate-in">
                  {s.hours && (
                    <div style={{ display:'flex', gap:8, alignItems:'flex-start', marginBottom:10 }}>
                      <Clock size={14} color="var(--muted)" style={{ flexShrink:0, marginTop:1 }}/>
                      <p style={{ margin:0, fontSize:12, color:'var(--muted)', lineHeight:1.5 }}>{s.hours}</p>
                    </div>
                  )}
                  <button onClick={e => {
                    e.stopPropagation()
                    window.open(`https://www.google.com/maps/dir/?api=1&destination=${s.lat},${s.lon}&travelmode=walking`,'_blank')
                  }} className="btn-primary" style={{
                    display:'flex', alignItems:'center', justifyContent:'center', gap:8
                  }}>
                    <Navigation size={16}/> Get Directions
                  </button>
                </div>
              )}
            </div>
          )
        })}

        {!loading && !error && stores.length===0 && (
          <div style={{ textAlign:'center', padding:'40px 20px', color:'var(--muted)' }}>
            <p style={{ fontSize:40, marginBottom:12 }}>🗺️</p>
            <p style={{ fontWeight:600 }}>No stores found nearby</p>
          </div>
        )}
      </div>
    </div>
  )
}
