import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Home, Search, ScanLine, ShoppingCart, Settings } from 'lucide-react'

const tabs = [
  { path: '/',         icon: Home,         label: 'Home'     },
  { path: '/search',   icon: Search,       label: 'Search'   },
  { path: '/scan',     icon: ScanLine,     label: 'Scan'     },
  { path: '/basket',   icon: ShoppingCart, label: 'Basket'   },
  { path: '/settings', icon: Settings,     label: 'Settings' },
]

export default function BottomNav() {
  const location = useLocation()
  const navigate = useNavigate()
  const [basketCount, setBasketCount] = useState(0)

  const updateCount = () => {
    const items = JSON.parse(localStorage.getItem('basket') || '[]')
    setBasketCount(items.reduce((s, i) => s + i.quantity, 0))
  }

  useEffect(() => {
    updateCount()
    window.addEventListener('basketUpdated', updateCount)
    window.addEventListener('storage', updateCount)
    return () => {
      window.removeEventListener('basketUpdated', updateCount)
      window.removeEventListener('storage', updateCount)
    }
  }, [])

  return (
    <nav style={{
      position: 'fixed', bottom: 0, left: 0, right: 0,
      background: 'rgba(13,13,15,0.96)',
      backdropFilter: 'blur(20px)',
      borderTop: '1px solid var(--border)',
      display: 'flex',
      padding: '8px 0 calc(8px + env(safe-area-inset-bottom))',
      zIndex: 100,
    }}>
      {tabs.map(({ path, icon: Icon, label }) => {
        const active = location.pathname === path
        const isBasket = path === '/basket'
        return (
          <button key={path} onClick={() => navigate(path)} style={{
            flex: 1, display: 'flex', flexDirection: 'column',
            alignItems: 'center', gap: 4,
            background: 'none', border: 'none', cursor: 'pointer',
            color: active ? 'var(--red)' : 'var(--muted)',
            transition: 'color 0.15s', padding: '4px 0',
            position: 'relative',
          }}>
            {path === '/scan' ? (
              <div style={{
                background: active ? 'var(--red)' : 'var(--surface)',
                border: `2px solid ${active ? 'var(--red)' : 'var(--border)'}`,
                borderRadius: 14, padding: 10, marginTop: -20,
                transition: 'all 0.15s',
              }}>
                <Icon size={22} color={active ? 'white' : 'var(--text)'} />
              </div>
            ) : (
              <div style={{ position: 'relative' }}>
                <Icon size={20} />
                {isBasket && basketCount > 0 && (
                  <span style={{
                    position: 'absolute', top: -6, right: -8,
                    background: 'var(--red)', color: 'white',
                    borderRadius: 10, fontSize: 9, fontWeight: 700,
                    minWidth: 16, height: 16, lineHeight: '16px',
                    textAlign: 'center', padding: '0 3px',
                  }}>
                    {basketCount > 99 ? '99+' : basketCount}
                  </span>
                )}
              </div>
            )}
            <span style={{ fontSize: 10, fontWeight: active ? 600 : 400 }}>{label}</span>
          </button>
        )
      })}
    </nav>
  )
}
