import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { X, Youtube, ExternalLink } from 'lucide-react'
import { getCuratedRecipe, getRecipeText } from '../data/recipes'
import { useBasket } from '../hooks/useBasket'
import { api } from '../api/client'

export default function RecipeView() {
  const { recipeId } = useParams()
  const navigate = useNavigate()
  const { addProduct } = useBasket()
  const lang = localStorage.getItem('lang') || 'en'

  const recipe = getCuratedRecipe(recipeId)
  const [matches, setMatches] = useState({})
  const [adding, setAdding] = useState(null)

  useEffect(() => {
    if (!recipe) return
    recipe.ingredients.forEach(ing => {
      api.search({ q: ing.searchTerm, lang, limit: 1 }).then(res => {
        setMatches(m => ({ ...m, [ing.searchTerm]: res.results?.[0] || null }))
      }).catch(() => {
        setMatches(m => ({ ...m, [ing.searchTerm]: null }))
      })
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recipeId])

  if (!recipe) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: 'var(--muted)' }}>
        <p>Recipe not found.</p>
        <button onClick={() => navigate(-1)} className="btn-ghost">Go back</button>
      </div>
    )
  }

  const text = getRecipeText(recipe, lang)
  const isPending = !recipe.text[lang]

  const handleAdd = async (ing) => {
    const product = matches[ing.searchTerm]
    if (!product) return
    setAdding(ing.searchTerm)
    addProduct({ gtin: product.gtin, name_en: product.name_en, name: product.name })
    setTimeout(() => setAdding(null), 600)
  }

  return (
    <div style={{ paddingBottom: 40 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 16px 0' }}>
        <button onClick={() => navigate(-1)} className="btn-ghost" style={{ width: 'auto', padding: 8 }}>
          <X size={20} />
        </button>
      </div>

      <div style={{ padding: '8px 20px 20px' }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: '8px 0 4px' }}>{text.name}</h1>
        <p style={{ margin: 0, color: 'var(--muted)', fontSize: 13 }}>
          {recipe.area} &middot; Serves {recipe.servings}
        </p>

        {isPending && (
          <div style={{
            marginTop: 12, padding: '8px 12px', borderRadius: 10,
            background: '#fff8e1', fontSize: 12, color: 'var(--muted)',
          }}>
            This recipe isn't available in your language yet &mdash; showing English.
          </div>
        )}

        <div style={{ marginTop: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 10 }}>Ingredients</h2>
          {recipe.ingredients.map(ing => {
            const product = matches[ing.searchTerm]
            const label = lang === 'de' ? ing.nameDe : ing.nameEn
            return (
              <div key={ing.searchTerm} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '10px 0', borderBottom: '1px solid #eee',
              }}>
                <div>
                  <p style={{ margin: 0, fontSize: 14 }}>{label}</p>
                  <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>{ing.measure}</p>
                </div>
                {product ? (
                  <button
                    onClick={() => handleAdd(ing)}
                    className="btn-ghost"
                    style={{ width: 'auto', padding: '6px 12px', fontSize: 12 }}
                  >
                    {adding === ing.searchTerm ? 'Added' : 'Add'}
                  </button>
                ) : matches[ing.searchTerm] === undefined ? (
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>Searching...</span>
                ) : (
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>Not found</span>
                )}
              </div>
            )
          })}
        </div>

        <div style={{ marginTop: 24 }}>
          <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 10 }}>Steps</h2>
          <ol style={{ paddingLeft: 20, margin: 0 }}>
            {text.steps.map((step, i) => (
              <li key={i} style={{ marginBottom: 10, fontSize: 14, lineHeight: 1.5 }}>{step}</li>
            ))}
          </ol>
        </div>

        {recipe.seeAlso && recipe.seeAlso.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <h2 style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, color: 'var(--muted)' }}>See also</h2>
            {recipe.seeAlso.map((link, i) => (
              <a
                key={i}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  fontSize: 13, color: '#0066cc', textDecoration: 'none',
                  marginBottom: 6,
                }}
              >
                <Youtube size={16} />
                {link.label}
                <ExternalLink size={12} />
              </a>
            ))}
          </div>
        )}

        <p style={{ marginTop: 24, fontSize: 11, color: 'var(--muted)' }}>
          Recipe: {recipe.source.label}
        </p>
      </div>
    </div>
  )
}
