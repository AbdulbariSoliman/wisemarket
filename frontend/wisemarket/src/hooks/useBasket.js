import { useState, useEffect } from 'react'

export function useBasket() {
  const [items, setItems] = useState(() =>
    JSON.parse(localStorage.getItem('basket') || '[]')
  )

  useEffect(() => {
    localStorage.setItem('basket', JSON.stringify(items))
    window.dispatchEvent(new Event('basketUpdated'))
  }, [items])

  const addProduct = (product) => {
    const gtin = product.gtin
    const name = product.name || product.name_en || gtin
    setItems(prev => {
      const ex = prev.find(i => i.gtin === gtin)
      if (ex) return prev.map(i => i.gtin === gtin ? {...i, quantity: i.quantity + 1} : i)
      return [...prev, { gtin, quantity: 1, name }]
    })
  }

  const removeProduct = (gtin) => setItems(prev => prev.filter(i => i.gtin !== gtin))

  const updateQuantity = (gtin, delta) => {
    setItems(prev => prev
      .map(i => i.gtin === gtin ? {...i, quantity: Math.max(0, i.quantity + delta)} : i)
      .filter(i => i.quantity > 0)
    )
  }

  const clearBasket = () => setItems([])
  const totalItems = items.reduce((s, i) => s + i.quantity, 0)

  return { items, setItems, addProduct, removeProduct, updateQuantity, clearBasket, totalItems }
}
