import { ChevronDown } from 'lucide-react'
import { useParts } from '../hooks/usePartContext'
import VinSearch from './VinSearch'
import NotificationBell from './NotificationBell'
import LastScoredBadge from './LastScoredBadge'

export default function TopBar({ title }) {
  const { parts, selectedPartCode, setSelectedPartCode, loading } = useParts()

  return (
    <header className="h-16 shrink-0 bg-surface flex items-center justify-between px-6 gap-4">
      <div className="shrink-0">
        <div className="text-xs text-ink-faint mb-0.5">Predictive Failure Engine</div>
        <h1 className="font-semibold text-lg text-ink tracking-tight">{title}</h1>
      </div>

      <div className="flex-1 flex justify-center">
        <VinSearch />
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <LastScoredBadge />
        <NotificationBell />
        <span className="text-xs text-ink-faint uppercase tracking-wide font-medium">Part</span>
        <div className="relative">
          <select
            value={selectedPartCode || ''}
            onChange={(e) => setSelectedPartCode(e.target.value)}
            disabled={loading}
            className="appearance-none bg-surface-sunken border border-line rounded-lg pl-3.5 pr-9 py-2 text-sm font-medium text-ink focus:outline-none focus:border-brand cursor-pointer disabled:opacity-50"
          >
            {parts.map((p) => (
              <option key={p.part_code} value={p.part_code}>
                {p.part_name} · {p.part_code}
              </option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint pointer-events-none" />
        </div>
      </div>
    </header>
  )
}
