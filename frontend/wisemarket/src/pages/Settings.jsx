import { useState } from 'react'
import { Check } from 'lucide-react'

const LANGUAGES = [
  { code: 'en', label: 'English',  flag: '🇬🇧' },
  { code: 'de', label: 'Deutsch',  flag: '🇨🇭' },
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
  { code: 'it', label: 'Italiano', flag: '🇮🇹' },
]

const DIETARY = [
  { key: 'halal',           label: '☪️ Halal'                 },
  { key: 'vegan',           label: '🌱 Vegan'                  },
  { key: 'vegetarian',      label: '🥦 Vegetarian'             },
  { key: 'gluten_free',     label: '🌾 Gluten-Free'            },
  { key: 'lactose_free',    label: '🥛 Lactose-Free'           },
  { key: 'dairy_free',      label: '🚫 Dairy-Free'             },
  { key: 'nut_free',        label: '🥜 Nut-Free'               },
  { key: 'organic',         label: '🌿 Organic / Bio'          },
  { key: 'regional',        label: '🇨🇭 Swiss / Regional'      },
  { key: 'low_sugar',       label: '🍬 Low Sugar'              },
  { key: 'high_protein',    label: '💪 High Protein'           },
  { key: 'low_fat',         label: '💧 Low Fat'                },
  { key: 'high_fiber',      label: '🌾 High Fibre'             },
  { key: 'keto',            label: '🥑 Keto'                   },
  { key: 'is_kids_friendly',label: '👶 Kids Friendly'          },
  { key: 'fairtrade',       label: '⚖️ Fairtrade'              },
  { key: 'is_sports',       label: '🏋️ Sports Nutrition'       },
]

export default function Settings() {
  const [lang, setLangState] = useState(localStorage.getItem('lang') || 'en')
  const [theme, setThemeState] = useState(localStorage.getItem('theme') || 'dark')
  const [prefs, setPrefs] = useState(JSON.parse(localStorage.getItem('dietary') || '{}'))

  const setLang = (code) => {
    setLangState(code)
    localStorage.setItem('lang', code)
  }

  const setTheme = (t) => {
    setThemeState(t)
    localStorage.setItem('theme', t)
    document.documentElement.setAttribute('data-theme', t)
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
        <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>🌍 Language</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {LANGUAGES.map(({ code, label, flag }) => (
            <button key={code} onClick={() => setLang(code)} style={{
              background: lang === code ? 'rgba(230,57,70,0.12)' : 'var(--dark)',
              border: `1px solid ${lang === code ? 'var(--red)' : 'var(--border)'}`,
              borderRadius: 12, padding: '12px 16px', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              transition: 'all 0.15s', color: 'var(--text)',
            }}>
              <span style={{ fontSize: 14 }}>{flag} {label}</span>
              {lang === code && <Check size={16} color="var(--red)" />}
            </button>
          ))}
        </div>
      </div>

      {/* Theme */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>🌓 Appearance</h2>
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
        <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>🥗 Dietary Preferences</h2>
        <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 14 }}>
          Filters search results automatically
        </p>
        {DIETARY.map(({ key, label }) => (
          <button key={key} onClick={() => togglePref(key)} style={{
            background: 'none', border: 'none', cursor: 'pointer', width: '100%',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '12px 0', borderBottom: '1px solid var(--border)', color: 'var(--text)',
          }}>
            <span style={{ fontSize: 14 }}>{label}</span>
            <div style={{
              width: 44, height: 24, borderRadius: 12,
              background: prefs[key] ? 'var(--red)' : 'var(--border)',
              position: 'relative', transition: 'background 0.2s', flexShrink: 0,
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

      {/* About */}
      <div className="card">
        <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>ℹ️ About</h2>
        {[
          ['App',      'WiseMarket v2.0'],
          ['Products', '~13,000 Swiss products'],
          ['Prices',   'Migros (live), more coming'],
          ['AI',       'Groq · gpt-oss-120b'],
          ['DB',       'Supabase PostgreSQL'],
        ].map(([k, v]) => (
          <div key={k} style={{
            display: 'flex', justifyContent: 'space-between',
            padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 13,
          }}>
            <span style={{ color: 'var(--muted)' }}>{k}</span>
            <span style={{ fontWeight: 500 }}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
