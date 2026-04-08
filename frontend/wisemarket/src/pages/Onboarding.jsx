import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check } from 'lucide-react'

const LANGUAGES = [
  { code:'en', flag:'🇬🇧', label:'English' },
  { code:'de', flag:'🇨🇭', label:'Deutsch' },
  { code:'fr', flag:'🇫🇷', label:'Français' },
  { code:'it', flag:'🇮🇹', label:'Italiano' },
]

const DIETARY_GROUPS = [
  {
    group: 'Religion & Culture',
    items: [
      { key:'halal', icon:'☪️', label:'Halal', sub:'Certified halal only' },
      { key:'vegan', icon:'🌱', label:'Vegan', sub:'No animal products' },
      { key:'vegetarian', icon:'🥦', label:'Vegetarian', sub:'No meat or fish' },
    ]
  },
  {
    group: 'Allergies & Intolerances',
    items: [
      { key:'gluten_free', icon:'🌾', label:'Gluten-Free', sub:'No wheat, barley, rye' },
      { key:'lactose_free', icon:'🥛', label:'Lactose-Free', sub:'No lactose' },
      { key:'dairy_free',   icon:'🚫', label:'Dairy-Free',   sub:'No dairy products' },
      { key:'nut_free',     icon:'🥜', label:'Nut-Free',     sub:'No nuts' },
    ]
  },
  {
    group: 'Lifestyle',
    items: [
      { key:'organic',      icon:'🌿', label:'Organic / Bio',   sub:'Certified organic' },
      { key:'regional',     icon:'🇨🇭', label:'Swiss Regional', sub:'Aus der Region' },
      { key:'high_protein', icon:'💪', label:'High Protein',    sub:'Sports & fitness' },
      { key:'low_sugar',    icon:'🍬', label:'Low Sugar',       sub:'Reduced sugar' },
      { key:'fairtrade',    icon:'⚖️', label:'Fairtrade',       sub:'Ethical sourcing' },
    ]
  },
]

const STORES = [
  { id:'migros', name:'Migros',  icon:'🟠', color:'#FF6600' },
  { id:'coop',   name:'Coop',    icon:'🔴', color:'#E2001A' },
  { id:'aldi',   name:'Aldi',    icon:'🔵', color:'#00539F' },
  { id:'lidl',   name:'Lidl',    icon:'🔵', color:'#0050AA' },
  { id:'denner', name:'Denner',  icon:'🟤', color:'#C8102E' },
  { id:'volg',   name:'Volg',    icon:'🟢', color:'#2E7D32' },
]

const T = {
  en: {
    step1title: 'Welcome to WiseMarket',
    step1sub: 'Switzerland\'s smartest grocery app',
    langLabel: 'Choose your language',
    next: 'Next →',
    step2title: 'Your preferences',
    step2sub: 'We\'ll personalise your experience',
    dietLabel: 'Dietary preferences',
    storeLabel: 'Your usual store',
    skip: 'Skip — set up later',
    done: 'Get started →',
    privacy: '🔒 Your data stays on your device',
    gift: '🎁 You get 2 months Pro free — no card needed',
  },
  de: {
    step1title: 'Willkommen bei WiseMarket',
    step1sub: 'Die klügste Einkaufs-App der Schweiz',
    langLabel: 'Wählen Sie Ihre Sprache',
    next: 'Weiter →',
    step2title: 'Ihre Präferenzen',
    step2sub: 'Wir personalisieren Ihre Erfahrung',
    dietLabel: 'Ernährungsgewohnheiten',
    storeLabel: 'Ihr bevorzugter Laden',
    skip: 'Überspringen',
    done: 'Loslegen →',
    privacy: '🔒 Ihre Daten bleiben auf Ihrem Gerät',
    gift: '🎁 2 Monate Pro gratis — keine Karte nötig',
  },
  fr: {
    step1title: 'Bienvenue sur WiseMarket',
    step1sub: 'L\'application courses la plus intelligente de Suisse',
    langLabel: 'Choisissez votre langue',
    next: 'Suivant →',
    step2title: 'Vos préférences',
    step2sub: 'Nous personnalisons votre expérience',
    dietLabel: 'Préférences alimentaires',
    storeLabel: 'Votre magasin habituel',
    skip: 'Ignorer',
    done: 'Commencer →',
    privacy: '🔒 Vos données restent sur votre appareil',
    gift: '🎁 2 mois Pro gratuits — sans carte',
  },
  it: {
    step1title: 'Benvenuto su WiseMarket',
    step1sub: 'L\'app spesa più intelligente della Svizzera',
    langLabel: 'Scegli la tua lingua',
    next: 'Avanti →',
    step2title: 'Le tue preferenze',
    step2sub: 'Personalizziamo la tua esperienza',
    dietLabel: 'Preferenze alimentari',
    storeLabel: 'Il tuo negozio abituale',
    skip: 'Salta',
    done: 'Inizia →',
    privacy: '🔒 I tuoi dati rimangono sul dispositivo',
    gift: '🎁 2 mesi Pro gratis — senza carta',
  },
}

export default function Onboarding({ onDone }) {
  const navigate  = useNavigate()
  const [step, setStep]   = useState(1)
  const [lang, setLang]   = useState(() => {
    const b = navigator.language?.substring(0,2)
    return ['en','de','fr','it'].includes(b) ? b : 'en'
  })
  const [prefs, setPrefs] = useState({})
  const [store, setStore] = useState('')
  const t = T[lang] || T.en

  const togglePref = (key) => {
    setPrefs(p => ({ ...p, [key]: !p[key] }))
  }

  const finish = () => {
    localStorage.setItem('lang', lang)
    localStorage.setItem('dietary', JSON.stringify(prefs))
    if (store) localStorage.setItem('preferred_store', store)
    localStorage.setItem('onboarded', '1')
    if (onDone) onDone()
    navigate('/')
  }

  if (step === 1) return (
    <div style={{
      minHeight:'100dvh', display:'flex', flexDirection:'column',
      background:'var(--dark)', padding:'0 24px',
    }}>
      {/* Logo area */}
      <div style={{ flex:1, display:'flex', flexDirection:'column',
                    justifyContent:'center', alignItems:'center', textAlign:'center' }}>
        <div style={{ fontSize:64, marginBottom:16 }}>🛒</div>
        <h1 style={{ fontFamily:'Syne', fontSize:28, fontWeight:800, margin:'0 0 8px' }}>
          WiseMarket
        </h1>
        <p style={{ color:'var(--muted)', fontSize:16, margin:'0 0 48px' }}>
          {t.step1sub}
        </p>

        {/* Gift banner */}
        <div style={{
          background:'rgba(230,57,70,0.1)', border:'1px solid rgba(230,57,70,0.3)',
          borderRadius:16, padding:'14px 20px', marginBottom:40, width:'100%',
        }}>
          <p style={{ margin:0, fontSize:14, color:'var(--red)', fontWeight:600 }}>
            {t.gift}
          </p>
        </div>

        {/* Language selector */}
        <p style={{ fontSize:14, color:'var(--muted)', marginBottom:16, alignSelf:'flex-start' }}>
          {t.langLabel}
        </p>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:10, width:'100%', marginBottom:16 }}>
          {LANGUAGES.map(l => (
            <button key={l.code} onClick={() => setLang(l.code)} style={{
              padding:'14px', borderRadius:14, cursor:'pointer',
              border:`1px solid ${lang===l.code ? 'var(--red)' : 'var(--border)'}`,
              background: lang===l.code ? 'rgba(230,57,70,0.1)' : 'var(--surface)',
              display:'flex', alignItems:'center', justifyContent:'space-between',
              color:'var(--text)', transition:'all 0.15s',
            }}>
              <span style={{ fontSize:15 }}>{l.flag} {l.label}</span>
              {lang===l.code && <Check size={16} color="var(--red)"/>}
            </button>
          ))}
        </div>
      </div>

      {/* Privacy + Next */}
      <div style={{ paddingBottom:48 }}>
        <p style={{ textAlign:'center', fontSize:12, color:'var(--muted)', marginBottom:16 }}>
          {t.privacy}
        </p>
        <button onClick={() => setStep(2)} style={{
          width:'100%', padding:'16px', borderRadius:14, border:'none',
          background:'var(--red)', color:'white', fontSize:16, fontWeight:700,
          cursor:'pointer', fontFamily:'Syne',
        }}>
          {t.next}
        </button>
      </div>
    </div>
  )

  return (
    <div style={{ minHeight:'100dvh', display:'flex', flexDirection:'column', background:'var(--dark)' }}>

      {/* Header */}
      <div style={{ padding:'20px 24px 0', textAlign:'center' }}>
        {/* Progress */}
        <div style={{ display:'flex', gap:6, justifyContent:'center', marginBottom:20 }}>
          {[1,2].map(s => (
            <div key={s} style={{
              height:4, borderRadius:2, transition:'all 0.3s',
              width: s===step ? 32 : 16,
              background: s<=step ? 'var(--red)' : 'var(--border)',
            }}/>
          ))}
        </div>
        <h1 style={{ fontFamily:'Syne', fontSize:22, fontWeight:800, margin:'0 0 6px' }}>
          {t.step2title}
        </h1>
        <p style={{ color:'var(--muted)', fontSize:14, margin:'0 0 24px' }}>
          {t.step2sub}
        </p>
      </div>

      {/* Scrollable content */}
      <div style={{ flex:1, overflowY:'auto', padding:'0 20px' }}>

        {/* Dietary groups */}
        <p style={{ fontSize:13, fontWeight:600, color:'var(--muted)', marginBottom:12 }}>
          {t.dietLabel}
        </p>

        {DIETARY_GROUPS.map(group => (
          <div key={group.group} style={{ marginBottom:20 }}>
            <p style={{ fontSize:11, color:'var(--muted)', fontWeight:600,
                        textTransform:'uppercase', letterSpacing:1, marginBottom:8 }}>
              {group.group}
            </p>
            <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
              {group.items.map(item => (
                <button key={item.key} onClick={() => togglePref(item.key)} style={{
                  display:'flex', alignItems:'center', gap:12, padding:'12px 14px',
                  borderRadius:12, cursor:'pointer', transition:'all 0.15s',
                  border:`1px solid ${prefs[item.key] ? 'var(--red)' : 'var(--border)'}`,
                  background: prefs[item.key] ? 'rgba(230,57,70,0.08)' : 'var(--surface)',
                  color:'var(--text)',
                }}>
                  <span style={{ fontSize:20, flexShrink:0 }}>{item.icon}</span>
                  <div style={{ flex:1, textAlign:'left' }}>
                    <p style={{ margin:0, fontSize:14, fontWeight:600 }}>{item.label}</p>
                    <p style={{ margin:0, fontSize:11, color:'var(--muted)' }}>{item.sub}</p>
                  </div>
                  {prefs[item.key] && <Check size={16} color="var(--red)"/>}
                </button>
              ))}
            </div>
          </div>
        ))}

        {/* Preferred store */}
        <p style={{ fontSize:13, fontWeight:600, color:'var(--muted)', margin:'8px 0 12px' }}>
          {t.storeLabel}
        </p>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:8, marginBottom:32 }}>
          {STORES.map(s => (
            <button key={s.id} onClick={() => setStore(store===s.id ? '' : s.id)} style={{
              padding:'12px 8px', borderRadius:12, cursor:'pointer',
              border:`1px solid ${store===s.id ? s.color : 'var(--border)'}`,
              background: store===s.id ? `${s.color}18` : 'var(--surface)',
              display:'flex', flexDirection:'column', alignItems:'center', gap:4,
              color:'var(--text)', transition:'all 0.15s',
            }}>
              <span style={{ fontSize:22 }}>{s.icon}</span>
              <span style={{ fontSize:12, fontWeight: store===s.id ? 600 : 400,
                             color: store===s.id ? s.color : 'var(--muted)' }}>
                {s.name}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div style={{ padding:'12px 24px calc(12px + env(safe-area-inset-bottom))' }}>
        <button onClick={finish} style={{
          width:'100%', padding:'16px', borderRadius:14, border:'none',
          background:'var(--red)', color:'white', fontSize:16, fontWeight:700,
          cursor:'pointer', fontFamily:'Syne', marginBottom:12,
        }}>
          {t.done}
        </button>
        <button onClick={() => { localStorage.setItem('onboarded','1'); navigate('/') }} style={{
          width:'100%', padding:'12px', borderRadius:14, border:'none',
          background:'none', color:'var(--muted)', fontSize:14, cursor:'pointer',
        }}>
          {t.skip}
        </button>
      </div>
    </div>
  )
}
