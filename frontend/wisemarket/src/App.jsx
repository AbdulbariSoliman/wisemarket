import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import BottomNav   from './components/BottomNav'
import Home        from './pages/Home'
import Basket      from './pages/Basket'
import Profile     from './pages/Profile'
import Product     from './pages/Product'
import Scan        from './pages/Scan'
import Chat        from './pages/Chat'
import StoreMap    from './pages/StoreMap'
import Onboarding  from './pages/Onboarding'

export default function App() {
  const [onboarded, setOnboarded] = useState(!!localStorage.getItem('onboarded'))

  useEffect(() => {
    // Register service worker
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {})
    }
    // Auto-detect language
    if (!localStorage.getItem('lang')) {
      const lang = navigator.language?.substring(0, 2)
      localStorage.setItem('lang', ['en','de','fr','it'].includes(lang) ? lang : 'en')
    }
    // Apply theme
    const theme = localStorage.getItem('theme') || 'dark'
    document.documentElement.setAttribute('data-theme', theme)

    // Listen for onboarding completion
    const check = () => setOnboarded(!!localStorage.getItem('onboarded'))
    window.addEventListener('storage', check)
    return () => window.removeEventListener('storage', check)
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/onboarding" element={<Onboarding onDone={() => setOnboarded(true)} />} />
        <Route path="/"           element={onboarded ? <Home />    : <Navigate to="/onboarding" replace />} />
        <Route path="/basket"     element={onboarded ? <Basket />  : <Navigate to="/onboarding" replace />} />
        <Route path="/profile"    element={onboarded ? <Profile /> : <Navigate to="/onboarding" replace />} />
        <Route path="/product/:gtin" element={<Product />} />
        <Route path="/scan"       element={<Scan />} />
        <Route path="/chat"       element={<Chat />} />
        <Route path="/stores"     element={<StoreMap />} />
      </Routes>
      {onboarded && <BottomNav />}
    </BrowserRouter>
  )
}
