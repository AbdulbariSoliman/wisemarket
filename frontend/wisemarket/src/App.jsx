import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import BottomNav from './components/BottomNav'
import Home     from './pages/Home'
import Basket   from './pages/Basket'
import Profile  from './pages/Profile'
import Product  from './pages/Product'
import Scan     from './pages/Scan'
import Chat     from './pages/Chat'
import StoreMap    from './pages/StoreMap'
import Onboarding  from './pages/Onboarding'

export default function App() {
  useEffect(() => {
    // Register service worker for offline mode
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js')
        .then(() => console.log('SW registered'))
        .catch(() => {})
    }

    // Auto-detect language on first open
    if (!localStorage.getItem('lang')) {
      const browserLang = navigator.language?.substring(0, 2)
      const supported = ['en', 'de', 'fr', 'it']
      const detected = supported.includes(browserLang) ? browserLang : 'en'
      localStorage.setItem('lang', detected)
    }
    // Apply theme
    const theme = localStorage.getItem('theme') || 'dark'
    document.documentElement.setAttribute('data-theme', theme)
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={
          localStorage.getItem('onboarded') ? <Home /> : <Navigate to="/onboarding" replace />
        }/>
        <Route path="/basket"        element={<Basket />}  />
        <Route path="/profile"       element={<Profile />} />
        <Route path="/product/:gtin" element={<Product />} />
        <Route path="/scan"          element={<Scan />}    />
        <Route path="/chat"          element={<Chat />}    />
        <Route path="/stores"        element={<StoreMap />}/>
        <Route path="/onboarding"     element={<Onboarding />}/>
      </Routes>
      <BottomNav />
    </BrowserRouter>
  )
}
