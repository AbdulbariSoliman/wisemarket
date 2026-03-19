import { useLocation, useNavigate } from 'react-router-dom'
import { Home, Search, ScanLine, ShoppingCart, Settings } from 'lucide-react'

const tabs = [
  { path: '/',        icon: Home,         label: 'Home'     },
  { path: '/search',  icon: Search,       label: 'Search'   },
  { path: '/scan',    icon: ScanLine,     label: 'Scan'     },
  { path: '/basket',  icon: ShoppingCart, label: 'Basket'   },
  { path: '/settings',icon: Settings,     label: 'Settings' },
]

export default function BottomNav() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <nav style={{
      position: 'fixed', bottom: 0, left: 0, right: 0,
      background: 'rgba(13,13,15,0.95)',
      backdropFilter: 'blur(20px)',
      borderTop: '1px solid var(--border)',
      display: 'flex',
      padding: '8px 0 calc(8px + env(safe-area-inset-bottom))',
      zIndex: 100,
    }}>
      {tabs.map(({ path, icon: Icon, label }) => {
        const active = location.pathname === path
        return (
          <button key={path} onClick={() => navigate(path)} style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 4,
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: active ? 'var(--red)' : 'var(--muted)',
            transition: 'color 0.15s',
            padding: '4px 0',
          }}>
            {path === '/scan'
              ? <div style={{
                  background: active ? 'var(--red)' : 'var(--surface)',
                  border: `2px solid ${active ? 'var(--red)' : 'var(--border)'}`,
                  borderRadius: '14px',
                  padding: '10px',
                  marginTop: -20,
                  transition: 'all 0.15s',
                }}>
                  <Icon size={22} color={active ? 'white' : 'var(--text)'} />
                </div>
              : <Icon size={20} />
            }
            <span style={{ fontSize: 10, fontWeight: active ? 600 : 400 }}>{label}</span>
          </button>
        )
      })}
    </nav>
  )
}
