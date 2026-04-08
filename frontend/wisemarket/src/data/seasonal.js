export function getGreeting(lang = 'en', name = null) {
  const hour = new Date().getHours()
  const g = {
    en: { m: 'Good morning', a: 'Good afternoon', e: 'Good evening' },
    de: { m: 'Guten Morgen',  a: 'Guten Tag',       e: 'Guten Abend'  },
    fr: { m: 'Bonjour',       a: 'Bonjour',          e: 'Bonsoir'      },
    it: { m: 'Buongiorno',    a: 'Buongiorno',       e: 'Buonasera'    },
  }
  const t = g[lang] || g.en
  const base = hour < 12 ? t.m : hour < 18 ? t.a : t.e
  return name ? `${base}, ${name} 👋` : `${base} 👋`
}

const EVENTS = [
  { month:1,  day:1,   icon:'🎆', en:'Happy New Year!',                   de:'Frohes neues Jahr!',                    fr:'Bonne année!',                it:'Buon anno!',              suggestions:['champagner','salat','smoothie','detox'], tag:'newyear' },
  { month:2,  day:14,  icon:'💝', en:'Romantic dinner for 2',             de:'Romantisches Dinner für 2',             fr:'Dîner romantique pour 2',     it:'Cena romantica per 2',    suggestions:['schokolade','lachs','wein','erdbeeren'], tag:'valentine' },
  { month:3,  day:null,icon:'🌱', en:'Spring — Swiss asparagus arriving', de:'Frühling — Schweizer Spargeln kommen',  fr:'Printemps — asperges suisses',it:'Primavera — asparagi',    suggestions:['spargeln','spinat','rhabarber','salat'], tag:'spring', dayRange:[20,31] },
  { month:4,  day:null,icon:'🐣', en:'Easter — chocolate & festive meals',de:'Ostern — Schokolade & Festessen',       fr:'Pâques — chocolat & repas',   it:'Pasqua — cioccolato',     suggestions:['schokolade','eier','lamm','brot'], tag:'easter', dayRange:[1,20] },
  { month:5,  day:null,icon:'💐', en:"Mother's Day — brunch for mum",     de:'Muttertag — Brunch für Mama',           fr:'Fête des mères — brunch',     it:'Festa della mamma',       suggestions:['orangensaft','croissant','lachs','beeren'], tag:'mothersday', dayRange:[7,14] },
  { month:5,  day:15,  icon:'🔥', en:'BBQ season starts!',                de:'Grillsaison startet!',                  fr:'Saison barbecue!',            it:'Stagione barbecue!',      suggestions:['fleisch','würstchen','sauce','bier'] },
  { month:6,  day:null,icon:'🍓', en:'Swiss strawberries — best time!',   de:'Schweizer Erdbeeren — beste Zeit!',     fr:'Fraises suisses — top!',      it:'Fragole svizzere!',       suggestions:['erdbeeren','rahm','joghurt','müesli'], tag:'strawberry' },
  { month:7,  day:null,icon:'🥾', en:'Hiking season — mountain snacks',   de:'Wandersaison — Snacks für die Berge',   fr:'Randonnée — snacks montagne', it:'Escursioni — snack',      suggestions:['energieriegel','nüsse','wasser','schokolade'] },
  { month:8,  day:1,   icon:'🇨🇭',en:'Swiss National Day 🇨🇭',           de:'1. August — Schweizer Produkte 🇨🇭',    fr:'1er août 🇨🇭',               it:'1° agosto 🇨🇭',           suggestions:['rösti','bratwurst','gruyere','rivella'], tag:'swiss', regional:true },
  { month:8,  day:20,  icon:'🎒', en:'Back to school — lunchbox ideas',   de:'Zurück zur Schule — Lunchbox-Ideen',    fr:'Rentrée — boîte à lunch',     it:'Ritorno a scuola',        suggestions:['brot','käse','früchte','joghurt','saft'] },
  { month:9,  day:15,  icon:'🧀', en:'Raclette season starts! 🧀',        de:'Raclette-Saison beginnt! 🧀',           fr:'Saison raclette! 🧀',         it:'Stagione raclette! 🧀',   suggestions:['raclettekäse','kartoffeln','cornichons','schinken'] },
  { month:9,  day:null,icon:'🍇', en:'Harvest — regional & fresh',        de:'Ernte & Herbstgemüse — regional',       fr:'Vendanges & légumes',         it:'Vendemmia & verdure',     suggestions:['kürbis','pilze','trauben','äpfel','marroni'], tag:'harvest' },
  { month:10, day:31,  icon:'🎃', en:'Halloween treats 🎃',               de:'Halloween — Süsses oder Saures 🎃',     fr:'Halloween 🎃',               it:'Halloween 🎃',             suggestions:['kürbis','schokolade','gummibärchen','chips'] },
  { month:10, day:null,icon:'🌱', en:'Vegan October — go plant-based',    de:'Veganer Oktober — plant-based',         fr:'Octobre végane',              it:'Ottobre vegano',           suggestions:['tofu','hafermilch','linsen','kichererbsen'], dayRange:[1,31] },
  { month:11, day:25,  icon:'🏷️', en:'Black Friday — best deals today',   de:'Black Friday — Beste Deals heute',      fr:'Black Friday',               it:'Black Friday',             tag:'blackfriday' },
  { month:11, day:null,icon:'🍪', en:'Christmas baking starts',           de:'Weihnachtsbäckerei — Guetzli!',         fr:'Pâtisserie de Noël',          it:'Biscotti natalizi',        suggestions:['mehl','butter','zucker','schokolade'], dayRange:[1,24] },
  { month:12, day:null,icon:'🎄', en:'Christmas — fondue & raclette',     de:'Weihnachten — Fondue & Raclette',       fr:'Noël — fondue & raclette',    it:'Natale — fonduta',         suggestions:['fonduekäse','schokolade','mandeln','clementinen'], dayRange:[1,25] },
  { month:12, day:26,  icon:'🥂', en:"New Year's Eve — party time!",      de:'Silvester — Party-Snacks!',             fr:'Saint-Sylvestre!',            it:'Capodanno!',               suggestions:['champagner','chips','käse','lachs'] },
]

const SEASONAL_PRODUCE = {
  1:['lauch','rüebli','sellerie','pastinaken','rosenkohl'],
  2:['lauch','rüebli','chicorée','sellerie'],
  3:['spargeln','spinat','rhabarber','radieschen'],
  4:['spargeln','spinat','rhabarber','salat','erbsen'],
  5:['spargeln','erdbeeren','salat','erbsen','radieschen','zucchetti'],
  6:['erdbeeren','kirschen','erbsen','zucchetti','tomaten','gurken','salat'],
  7:['tomaten','gurken','zucchetti','peperoni','himbeeren','heidelbeeren','mais'],
  8:['tomaten','peperoni','auberginen','mais','zwetschgen','äpfel','trauben'],
  9:['kürbis','äpfel','birnen','trauben','marroni','pilze','lauch'],
  10:['kürbis','äpfel','marroni','pilze','lauch','rüebli'],
  11:['lauch','rüebli','rosenkohl','grünkohl','feldsalat'],
  12:['lauch','rüebli','rosenkohl','feldsalat','clementinen'],
}

const TIME_SUGGESTIONS = {
  morning:  ['milch','eier','brot','kaffee','joghurt','müesli','orangensaft'],
  lunch:    ['sandwich','salat','suppe','pasta'],
  afternoon:['früchte','joghurt','nüsse','schokolade','tee'],
  evening:  ['fleisch','gemüse','pasta','reis','fisch','wein'],
  weekend:  ['fondue','raclette','brunch','kuchen','champagner'],
}

export function getSeasonalContext(lang = 'en') {
  const now = new Date()
  const month = now.getMonth() + 1
  const day = now.getDate()
  const hour = now.getHours()
  const dow = now.getDay()
  const isWeekend = dow === 0 || dow === 6

  const event = EVENTS.find(e => {
    if (e.month !== month) return false
    if (e.day && e.day !== day) return false
    if (e.dayRange) {
      const [s, en] = e.dayRange
      if (day < s || day > en) return false
    }
    return true
  })

  let slot = 'morning'
  if (hour >= 11 && hour < 14) slot = 'lunch'
  else if (hour >= 14 && hour < 17) slot = 'afternoon'
  else if (hour >= 17) slot = 'evening'

  const produce = SEASONAL_PRODUCE[month] || []

  const suggestions = [...new Set([
    ...(event?.suggestions || []),
    ...(isWeekend ? TIME_SUGGESTIONS.weekend : TIME_SUGGESTIONS[slot] || []),
    ...produce.slice(0, 3),
  ])].slice(0, 8)

  return {
    event,
    banner: event ? (event[lang] || event.en) : null,
    bannerIcon: event?.icon || null,
    suggestions,
    seasonalProduce: produce,
    highlightRegional: event?.regional || false,
    isWeekend,
  }
}

const CARBON = {
  wasser:0.0001, salat:0.15, gurken:0.15, tomaten:0.22, rüebli:0.12,
  kartoffeln:0.18, zwiebeln:0.12, äpfel:0.19, erdbeeren:0.24, bananen:0.35,
  brot:0.60, pasta:0.65, reis:0.70, linsen:0.48, tofu:0.55, hafermilch:0.45,
  milch:1.05, joghurt:1.20, käse:1.50, butter:1.70, eier:1.30, lachs:1.80,
  schokolade:1.60, fisch:1.40,
  poulet:2.10, hühnchen:2.10, schweinefleisch:2.20, wurst:2.30,
  rindfleisch:13.5, lamm:10.4, hackfleisch:8.5,
}

const CAT_DEFAULTS = {
  meat:3.5, fish:1.4, dairy:1.2, dairy_alternative:0.5,
  fresh_produce:0.2, pantry:0.7, bakery:0.6, beverages:0.1, snacks:1.1,
}

const GRADE = v => v < 0.4 ? {score:'A',color:'#038141'} : v < 0.9 ? {score:'B',color:'#85BB2F'} :
  v < 1.8 ? {score:'C',color:'#FECB02'} : v < 2.6 ? {score:'D',color:'#EE8100'} : {score:'E',color:'#E63946'}

export function getCarbonScore(name, category) {
  const n = (name || '').toLowerCase()
  for (const [k, v] of Object.entries(CARBON)) {
    if (n.includes(k)) return { ...GRADE(v), kg: v }
  }
  const def = CAT_DEFAULTS[category]
  return def ? { ...GRADE(def), kg: def } : null
}
