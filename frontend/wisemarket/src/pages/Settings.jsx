import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check } from 'lucide-react'

const LANGUAGES = [
  { code: 'en', label: 'English',  flag: '🇬🇧' },
  { code: 'de', label: 'Deutsch',  flag: '🇨🇭' },
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
  { code: 'it', label: 'Italiano', flag: '🇮🇹' },
]

const DIETARY = [
  { key: 'halal',        label: '☪️ Halal'        },
  { key: 'vegan',        label: '🌱 Vegan'        },
  { key: 'vegetarian',   label: '🥦 Vegetarian'   },
  { key: 'gluten_free',  label: '🌾 Gluten-Free'  },
  { key: 'lactose_free', label: '🥛 Lactose-Free' },
  { key: 'nut_allergy',  label: '🥜 Nut Allergy'  },
  { key: 'low_sugar',    label: '🍬 Low Sugar'    },
  { key: 'high_protein', label: '💪 High Protein' },
]

export default function Settings() {
  const [lang, setLangState] = useState(localStorage.getItem('lang') || 'en')
  const [theme, setThemeState] = useState(localStorage.getItem('theme') || 'dark')
  const [prefs, setPrefs]    = useState(
    JSON.parse(localStorage.getItem('dietary') || '{}')
  )

  const setTheme = (t) => {
    setThemeState(t)
    localStorage.setItem('theme', t)
    document.documentElement.setAttribute('data-theme', t)
  }

  const setLang = (code) => {
    setLangState(code)
    localStorage.setItem('lang', code)
  }

  const togglePref = (key) => {
    const updated = { ...prefs, [key]: !prefs[key] }
    setPrefs(updated)
    localStorage.setItem('dietary', JSON.stringify(updated))
  }

  return (
    <div style={{ padding: '24px 16px 100px' }}>
      <h1 style={{ fontFamily: 'Syne', fontSize: 24, fontWeight: 800, marginBottom: 24 }}>
        ⚙️ Settings
      </h1>

      {/* Language */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>
          🌍 Language
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {LANGUAGES.map(({ code, label, flag }) => (
            <button key={code} onClick={() => setLang(code)} style={{
              background: lang === code ? 'rgba(230,57,70,0.12)' : 'var(--dark)',
              border: `1px solid ${lang === code ? 'var(--red)' : 'var(--border)'}`,
              borderRadius: 12, padding: '12px 16px', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              transition: 'all 0.15s',
            }}>
              <span style={{ fontSize: 14 }}>{flag} {label}</span>
              {lang === code && <Check size={16} color="var(--red)" />}
            </button>
          ))}
        </div>
      </div>

      {/* Theme */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>
          🌓 Appearance
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {[['dark','🌙 Dark'], ['light','☀️ Light']].map(([t, label]) => (
            <button key={t} onClick={() => setTheme(t)} style={{
              background: theme === t ? 'rgba(230,57,70,0.12)' : 'var(--dark)',
              border: `1px solid ${theme === t ? 'var(--red)' : 'var(--border)'}`,
              borderRadius: 12, padding: '12px 16px', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              transition: 'all 0.15s', color: 'var(--text)',
            }}>
              <span style={{ fontSize: 14 }}>{label}</span>
              {theme === t && <Check size={16} color="var(--red)" />}
            </button>
          ))}
        </div>
      </div>

      {/* Dietary preferences */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>
          🥗 Dietary Preferences
        </h2>
        <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 14 }}>
          Used to filter search results automatically
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {DIETARY.map(({ key, label }) => (
            <button key={key} onClick={() => togglePref(key)} style={{
              background: 'none', border: 'none', cursor: 'pointer',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '12px 0', borderBottom: '1px solid var(--border)',
              color: 'var(--text)',
            }}>
              <span style={{ fontSize: 14 }}>{label}</span>
              <div style={{
                width: 44, height: 24, borderRadius: 12,
                background: prefs[key] ? 'var(--red)' : 'var(--border)',
                position: 'relative', transition: 'background 0.2s',
              }}>
                <div style={{
                  position: 'absolute', top: 2,
                  left: prefs[key] ? 22 : 2,
                  width: 20, height: 20, borderRadius: '50%',
                  background: 'white', transition: 'left 0.2s',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                }} />
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* App info */}
      <div className="card">
        <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>
          ℹ️ About
        </h2>
        {[
          ['App',     'WiseMarket v2.0'],
          ['API',     'FastAPI + Groq'],
          ['DB',      'Supabase PostgreSQL'],
          ['Markets', 'Migros, Coop, Aldi, Lidl'],
        ].map(([k, v]) => (
          <div key={k} style={{
            display: 'flex', justifyContent: 'space-between',
            padding: '8px 0', borderBottom: '1px solid var(--border)',
            fontSize: 13,
          }}>
            <span style={{ color: 'var(--muted)' }}>{k}</span>
            <span style={{ fontWeight: 500 }}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
