import { Clock } from 'lucide-react'
import { useParts } from '../hooks/usePartContext'

// computed_date is stored at DATE granularity (not a timestamp), so this
// deliberately shows a formatted date rather than a fake "2 min ago" —
// that kind of precision doesn't exist in the underlying data.
export default function LastScoredBadge() {
  const { lastScoredDate, alertsLoading } = useParts()

  if (alertsLoading && !lastScoredDate) return null
  if (!lastScoredDate) return null

  const formatted = new Date(`${lastScoredDate}T00:00:00`).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-surface-sunken text-ink-faint text-xs font-medium">
      <Clock size={12} />
      Last scored: {formatted}
    </span>
  )
}
