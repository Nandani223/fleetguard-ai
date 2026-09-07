import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { useParts } from '../hooks/usePartContext'
import { pct } from '../constants'

const MAX_SHOWN = 6

export default function NotificationBell() {
  const { redTierVehicles, selectedPart } = useParts()
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const count = redTierVehicles.length

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative w-9 h-9 rounded-lg flex items-center justify-center text-ink-dim hover:text-ink hover:bg-surface-sunken transition-colors"
        aria-label="Red-tier alerts"
      >
        <Bell size={17} />
        {count > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-risk-red text-white text-[10px] font-bold flex items-center justify-center leading-none">
            {count > 99 ? '99+' : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute z-20 mt-1.5 w-80 right-0 rounded-xl border border-line bg-surface shadow-card overflow-hidden">
          <div className="px-4 py-3 border-b border-line">
            <p className="text-xs font-semibold text-ink">
              {count} Red-tier vehicle{count === 1 ? '' : 's'}
            </p>
            <p className="text-[11px] text-ink-faint">{selectedPart?.part_name}</p>
          </div>
          {count === 0 && (
            <p className="px-4 py-4 text-xs text-ink-dim">No Red-tier vehicles for this part right now.</p>
          )}
          {redTierVehicles.slice(0, MAX_SHOWN).map((p) => (
            <button
              key={p.vin}
              onClick={() => {
                setOpen(false)
                navigate(`/failure-probability?vin=${p.vin}`)
              }}
              className="w-full text-left px-4 py-2.5 hover:bg-surface-sunken/60 transition-colors border-b border-line last:border-b-0 flex items-center justify-between"
            >
              <span className="text-xs font-semibold text-ink font-mono">{p.vin}</span>
              <span className="text-xs font-bold text-risk-red tabular-nums">{pct(p.failure_probability)}</span>
            </button>
          ))}
          {count > MAX_SHOWN && (
            <button
              onClick={() => {
                setOpen(false)
                navigate('/failure-probability')
              }}
              className="w-full text-center px-4 py-2.5 text-xs font-semibold text-brand-dim hover:bg-surface-sunken/60 transition-colors"
            >
              View all {count} →
            </button>
          )}
        </div>
      )}
    </div>
  )
}
