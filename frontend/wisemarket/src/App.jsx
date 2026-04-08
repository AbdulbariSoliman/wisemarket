import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import BottomNav from './components/BottomNav'
import Home     from './pages/Home'
import Basket   from './pages/Basket'
import Profile  from './pages/Profile'
import Product  from './pages/Product'
import Scan     from './pages/Scan'
import Chat     from './pages/Chat'

export default function App() {
  useEffect(() => {
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
        <Route path="/"              element={<Home />}    />
        <Route path="/basket"        element={<Basket />}  />
        <Route path="/profile"       element={<Profile />} />
        <Route path="/product/:gtin" element={<Product />} />
        <Route path="/scan"          element={<Scan />}    />
        <Route path="/chat"          element={<Chat />}    />
      </Routes>
      <BottomNav />
    </BrowserRouter>
  )
}
