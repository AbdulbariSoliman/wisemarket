import { useState, useEffect, useRef } from 'react'
import { BrowserMultiFormatReader } from '@zxing/library'
import { X, Camera } from 'lucide-react'
import { api } from '../api/client'
import ProductCard from '../components/ProductCard'
import PriceBar from '../components/PriceBar'

export default function Scan() {
  const [scanning, setScanning]   = useState(false)
  const [result, setResult]       = useState(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')
  const [manualGtin, setManual]   = useState('')
  const videoRef = useRef()
  const readerRef = useRef()
  const lang = localStorage.getItem('lang') || 'en'

  const startScan = async () => {
    setScanning(true)
    setError('')
    readerRef.current = new BrowserMultiFormatReader()
    try {
      await readerRef.current.decodeFromVideoDevice(null, videoRef.current, (res, err) => {
        if (res) {
          stopScan()
          lookup(res.getText())
        }
      })
    } catch (e) {
      setError('Camera access denied. Please allow camera or enter GTIN manually.')
      setScanning(false)
    }
  }

  const stopScan = () => {
    readerRef.current?.reset()
    setScanning(false)
  }

  const lookup = async (barcode) => {
    setLoading(true)
    setResult(null)
    try {
      const data = await api.scan({ barcode, lang })
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => () => readerRef.current?.reset(), [])

  return (
    <div style={{ padding: '24px 16px 100px' }}>
      <h1 style={{ fontFamily: 'Syne', fontSize: 24, fontWeight: 800, marginBottom: 20 }}>
        📷 Scan Product
      </h1>

      {/* Camera / Scanner */}
      {scanning ? (
        <div style={{ position: 'relative', marginBottom: 20 }}>
          <video ref={videoRef} style={{
            width: '100%', borderRadius: 16, background: '#000',
            border: '2px solid var(--red)',
          }} />
          {/* Scan line animation */}
          <div style={{
            position: 'absolute', top: '50%', left: '10%', right: '10%',
            height: 2, background: 'var(--red)', boxShadow: '0 0 8px var(--red)',
            animation: 'scanLine 2s ease-in-out infinite',
          }} />
          <button onClick={stopScan} style={{
            position: 'absolute', top: 10, right: 10,
            background: 'rgba(0,0,0,0.7)', border: 'none',
            borderRadius: '50%', padding: 8, cursor: 'pointer',
          }}>
            <X size={18} color="white" />
          </button>
          <p style={{ textAlign: 'center', color: 'var(--muted)', fontSize: 13, marginTop: 10 }}>
            Point camera at barcode
          </p>
        </div>
      ) : (
        <button className="btn-primary" onClick={startScan}
          style={{ marginBottom: 16, display: 'flex', alignItems: 'center',
                   justifyContent: 'center', gap: 8 }}>
          <Camera size={18} /> Start Scanning
        </button>
      )}

      {/* Manual entry */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        <input value={manualGtin} onChange={e => setManual(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && lookup(manualGtin)}
          placeholder="Or enter GTIN / barcode manually"
          style={{ borderRadius: 12 }} />
        <button onClick={() => lookup(manualGtin)} className="btn-ghost"
          style={{ whiteSpace: 'nowrap', width: 'auto', padding: '0 16px' }}>
          Look up
        </button>
      </div>

      {error && (
        <div style={{ background: 'rgba(230,57,70,0.1)', border: '1px solid var(--red)',
                      borderRadius: 12, padding: 14, marginBottom: 16, fontSize: 14,
                      color: 'var(--red)' }}>
          {error}
        </div>
      )}

      {loading && (
        <div className="skeleton" style={{ height: 100, borderRadius: 16 }} />
      )}

      {/* Results */}
      {result && (
        <div className="animate-in">
          <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 12 }}>
            GTIN: {result.gtin}
          </p>
          {result.products?.map((p, i) => (
            <ProductCard key={i} product={p} />
          ))}

          {result.prices?.length > 0 && (
            <div className="card" style={{ marginTop: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>
                💰 Price Comparison
              </h3>
              <PriceBar
                prices={Object.fromEntries(result.prices.map(p => [p.store, p.price_chf]))}
                cheapest={result.prices.sort((a,b) => a.price_chf - b.price_chf)[0]?.store}
              />
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes scanLine {
          0%, 100% { top: 20%; }
          50% { top: 80%; }
        }
      `}</style>
    </div>
  )
}
