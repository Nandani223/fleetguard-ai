import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Loader2 } from 'lucide-react'
import { searchVehicles } from '../api/client'

export default function VinSearch() {
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    const q = query.trim()
    if (q.length < 2) {
      setMatches([])
      setOpen(false)
      return
    }
    setLoading(true)
    const handle = setTimeout(() => {
      searchVehicles(q)
        .then((res) => {
          setMatches(res.matches || [])
          setOpen(true)
        })
        .catch(() => setMatches([]))
        .finally(() => setLoading(false))
    }, 250)
    return () => clearTimeout(handle)
  }, [query])

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function goToVin(vin) {
    setOpen(false)
    setQuery('')
    navigate(`/failure-probability?vin=${vin}`)
  }

  return (
    <div className="relative w-64" ref={containerRef}>
      <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint pointer-events-none" />
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => matches.length > 0 && setOpen(true)}
        placeholder="Search VIN…"
        className="w-full bg-surface-sunken border border-line rounded-lg pl-9 pr-8 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-brand"
      />
      {loading && (
        <Loader2 size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint animate-spin" />
      )}

      {open && (
        <div className="absolute z-20 mt-1.5 w-80 right-0 rounded-xl border border-line bg-surface shadow-card overflow-hidden">
          {matches.length === 0 && !loading && (
            <p className="px-4 py-3 text-xs text-ink-dim">No vehicles match "{query}"</p>
          )}
          {matches.map((v) => (
            <button
              key={v.vin}
              onClick={() => goToVin(v.vin)}
              className="w-full text-left px-4 py-2.5 hover:bg-surface-sunken/60 transition-colors border-b border-line last:border-b-0"
            >
              <p className="text-xs font-semibold text-ink font-mono">{v.vin}</p>
              <p className="text-[11px] text-ink-faint">
                {v.model} · {v.region} · {v.total_km_driven.toLocaleString()} km
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
