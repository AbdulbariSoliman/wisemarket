import { useState } from 'react'
import { Check, ChevronRight } from 'lucide-react'

const LANGUAGES = [
  { code: 'en', label: 'English',  flag: '🇬🇧' },
  { code: 'de', label: 'Deutsch',  flag: '🇨🇭' },
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
  { code: 'it', label: 'Italiano', flag: '🇮🇹' },
]

const DIETARY = [
  { key: 'halal',            label: '☪️ Halal'                 },
  { key: 'vegan',            label: '🌱 Vegan'                  },
  { key: 'vegetarian',       label: '🥦 Vegetarian'             },
  { key: 'gluten_free',      label: '🌾 Gluten-Free'            },
  { key: 'lactose_free',     label: '🥛 Lactose-Free'           },
  { key: 'dairy_free',       label: '🚫 Dairy-Free'             },
  { key: 'nut_free',         label: '🥜 Nut-Free'               },
  { key: 'organic',          label: '🌿 Organic / Bio'          },
  { key: 'regional',         label: '🇨🇭 Swiss Regional'        },
  { key: 'low_sugar',        label: '🍬 Low Sugar'              },
  { key: 'high_protein',     label: '💪 High Protein'           },
  { key: 'low_fat',          label: '💧 Low Fat'                },
  { key: 'high_fiber',       label: '🌾 High Fibre'             },
  { key: 'keto',             label: '🥑 Keto'                   },
  { key: 'is_kids_friendly', label: '👶 Kids Friendly'          },
  { key: 'fairtrade',        label: '⚖️ Fairtrade'              },
  { key: 'is_sports',        label: '🏋️ Sports Nutrition'       },
]

export default function Profile() {
  const [lang, setLangState]   = useState(localStorage.getItem('lang') || 'en')
  const [theme, setThemeState] = useState(localStorage.getItem('theme') || 'dark')
  const [prefs, setPrefs]      = useState(JSON.parse(localStorage.getItem('dietary') || '{}'))
  const [section, setSection]  = useState(null)

  const setLang = (code) => {
    setLangState(code)
    localStorage.setItem('lang', code)
    window.location.reload()
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

  const activePrefs = Object.entries(prefs).filter(([,v]) => v).length

  return (
    <div style={{ padding: '24px 16px 100px' }}>
      <h1 style={{ fontFamily: 'Syne', fontSize: 24, fontWeight: 800, marginBottom: 4 }}>
        Profile
      </h1>
      <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 24 }}>
        Your preferences · WiseMarket
      </p>

      {/* Pro trial banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(230,57,70,0.15), rgba(230,57,70,0.05))',
        border: '1px solid rgba(230,57,70,0.3)',
        borderRadius: 16, padding: '16px', marginBottom: 16,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <p style={{ margin: 0, fontFamily: 'Syne', fontSize: 16, fontWeight: 700 }}>
              ✨ WiseMarket accounts
            </p>
            <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--muted)' }}>
              Sync across devices and unlock extra features
            </p>
          </div>
          <span style={{
            border: '1px solid rgba(230,57,70,0.4)', color: 'var(--red)',
            borderRadius: 10, padding: '6px 12px', fontSize: 12, fontWeight: 600,
            whiteSpace: 'nowrap',
          }}>
            Coming soon
          </span>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {['Price alerts', 'Price history', 'Budget mode', 'Recipe calculator'].map(f => (
            <span key={f} style={{
              fontSize: 11, padding: '3px 10px', borderRadius: 20,
              background: 'rgba(230,57,70,0.1)', color: 'var(--red)',
            }}>⭐ {f}</span>
          ))}
        </div>
      </div>

      {/* Language */}
      <div className="card" style={{ marginBottom: 12 }}>
        <button onClick={() => setSection(section === 'lang' ? null : 'lang')}
          style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer',
                   display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                   color: 'var(--text)', padding: 0 }}>
          <div>
            <p style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>🌍 Language</p>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--muted)' }}>
              {LANGUAGES.find(l => l.code === lang)?.flag} {LANGUAGES.find(l => l.code === lang)?.label}
            </p>
          </div>
          <ChevronRight size={16} color="var(--muted)"
            style={{ transform: section === 'lang' ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }} />
        </button>
        {section === 'lang' && (
          <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {LANGUAGES.map(({ code, label, flag }) => (
              <button key={code} onClick={() => setLang(code)} style={{
                background: lang === code ? 'rgba(230,57,70,0.12)' : 'var(--dark)',
                border: `1px solid ${lang === code ? 'var(--red)' : 'var(--border)'}`,
                borderRadius: 12, padding: '10px 14px', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                color: 'var(--text)',
              }}>
                <span style={{ fontSize: 13 }}>{flag} {label}</span>
                {lang === code && <Check size={14} color="var(--red)" />}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Dietary preferences */}
      <div className="card" style={{ marginBottom: 12 }}>
        <button onClick={() => setSection(section === 'diet' ? null : 'diet')}
          style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer',
                   display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                   color: 'var(--text)', padding: 0 }}>
          <div>
            <p style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>🥗 Dietary Preferences</p>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--muted)' }}>
              {activePrefs > 0 ? `${activePrefs} filter${activePrefs > 1 ? 's' : ''} active` : 'None selected'}
            </p>
          </div>
          <ChevronRight size={16} color="var(--muted)"
            style={{ transform: section === 'diet' ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }} />
        </button>
        {section === 'diet' && (
          <div style={{ marginTop: 14 }}>
            {DIETARY.map(({ key, label }) => (
              <button key={key} onClick={() => togglePref(key)} style={{
                background: 'none', border: 'none', cursor: 'pointer', width: '100%',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '11px 0', borderBottom: '1px solid var(--border)', color: 'var(--text)',
              }}>
                <span style={{ fontSize: 13 }}>{label}</span>
                <div style={{
                  width: 42, height: 24, borderRadius: 12, flexShrink: 0,
                  background: prefs[key] ? 'var(--red)' : 'var(--border)',
                  position: 'relative', transition: 'background 0.2s',
                }}>
                  <div style={{
                    position: 'absolute', top: 2, left: prefs[key] ? 20 : 2,
                    width: 20, height: 20, borderRadius: '50%',
                    background: 'white', transition: 'left 0.2s',
                  }} />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Appearance */}
      <div className="card" style={{ marginBottom: 12 }}>
        <button onClick={() => setSection(section === 'theme' ? null : 'theme')}
          style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer',
                   display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                   color: 'var(--text)', padding: 0 }}>
          <div>
            <p style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>
              {theme === 'dark' ? '🌙' : '☀️'} Appearance
            </p>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--muted)' }}>
              {theme === 'dark' ? 'Dark mode' : 'Light mode'}
            </p>
          </div>
          <ChevronRight size={16} color="var(--muted)"
            style={{ transform: section === 'theme' ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }} />
        </button>
        {section === 'theme' && (
          <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {[['dark','🌙 Dark'], ['light','☀️ Light']].map(([t, label]) => (
              <button key={t} onClick={() => setTheme(t)} style={{
                background: theme === t ? 'rgba(230,57,70,0.12)' : 'var(--dark)',
                border: `1px solid ${theme === t ? 'var(--red)' : 'var(--border)'}`,
                borderRadius: 12, padding: '10px 14px', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                color: 'var(--text)',
              }}>
                <span style={{ fontSize: 13 }}>{label}</span>
                {theme === t && <Check size={14} color="var(--red)" />}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Privacy */}
      <div className="card" style={{ marginBottom: 12 }}>
        <p style={{ margin: '0 0 8px', fontSize: 14, fontWeight: 600 }}>🔒 Privacy</p>
        <p style={{ margin: '0 0 12px', fontSize: 13, color: 'var(--muted)', lineHeight: 1.6 }}>
          WiseMarket never sells your shopping data. Your preferences stay on your device — delete everything anytime.
        </p>
        <button style={{
          background: 'none', border: '1px solid var(--border)', borderRadius: 10,
          padding: '8px 16px', fontSize: 13, color: 'var(--muted)', cursor: 'pointer',
        }}>
          Delete my data
        </button>
      </div>

      {/* About */}
      <div className="card">
        <p style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600 }}>ℹ️ About WiseMarket</p>
        {[
          ['Version',  '2.0.0'],
          ['Products', '~13,000 Swiss products'],
          ['Prices',   'Migros · other stores: sample data'],
          ['AI',       'Groq · llama-3.3-70b'],
          ['Data',     'Your data stays yours'],
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
