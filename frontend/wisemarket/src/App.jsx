import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import BottomNav from './components/BottomNav'
import Home     from './pages/Home'
import Search   from './pages/Search'
import Scan     from './pages/Scan'
import Chat     from './pages/Chat'
import Basket   from './pages/Basket'
import Product  from './pages/Product'
import Settings from './pages/Settings'

export default function App() {
  useEffect(() => {
    const theme = localStorage.getItem('theme') || 'dark'
    document.documentElement.setAttribute('data-theme', theme)
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"              element={<Home />}     />
        <Route path="/search"        element={<Search />}   />
        <Route path="/scan"          element={<Scan />}     />
        <Route path="/chat"          element={<Chat />}     />
        <Route path="/basket"        element={<Basket />}   />
        <Route path="/product/:gtin" element={<Product />}  />
        <Route path="/settings"      element={<Settings />} />
      </Routes>
      <BottomNav />
    </BrowserRouter>
  )
}
