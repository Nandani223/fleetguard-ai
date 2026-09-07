import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CalendarClock } from 'lucide-react'
import { getMaintenanceCalendar } from '../api/client'
import { pct } from '../constants'
import RiskBadge from '../components/RiskBadge'
import Loading from '../components/Loading'
import EmptyState from '../components/EmptyState'

const BUCKETS = [
  { key: 'overdue', label: 'Due Now (≤ 7 days)', test: (d) => d <= 7 },
  { key: 'month', label: 'Within a Month (8–30 days)', test: (d) => d > 7 && d <= 30 },
  { key: 'quarter', label: '1–3 Months (31–90 days)', test: (d) => d > 30 && d <= 90 },
  { key: 'half', label: '3–6 Months (91–180 days)', test: (d) => d > 90 && d <= 180 },
  { key: 'later', label: '6+ Months', test: (d) => d > 180 },
]

const TIERS = ['All', 'Red', 'Amber', 'Green']

export default function MaintenanceCalendarPage() {
  const [items, setItems] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [tier, setTier] = useState('All')
  const navigate = useNavigate()

  useEffect(() => {
    setLoading(true)
    getMaintenanceCalendar()
      .then((res) => setItems(res.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading label="Loading maintenance schedule" />
  if (error) return <EmptyState title="Couldn't load the calendar" body={error} />
  if (!items || items.length === 0) {
    return (
      <EmptyState
        title="No scheduled maintenance yet"
        body="This calendar reads RUL numbers already computed on the RUL Explorer screen. Run scoring and 'Run RUL for this part' for a part first, and its vehicles will show up here."
      />
    )
  }

  const filtered = tier === 'All' ? items : items.filter((i) => i.risk_tier === tier)

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="font-semibold text-ink text-sm mb-1">
            {filtered.length} vehicle/part{filtered.length === 1 ? '' : 's'} with service due
          </h2>
          <p className="text-xs text-ink-faint">
            Every part, every vehicle — ranked by remaining useful life, already computed on RUL Explorer.
          </p>
        </div>
        <div className="flex bg-surface-sunken rounded-lg p-1">
          {TIERS.map((t) => (
            <button
              key={t}
              onClick={() => setTier(t)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                tier === t ? 'bg-surface text-brand-dim shadow-sm' : 'text-ink-dim hover:text-ink'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 && (
        <EmptyState title={`No ${tier}-tier items`} body="Nothing in this risk tier is currently scheduled." />
      )}

      <div className="space-y-5">
        {BUCKETS.map((bucket) => {
          const bucketItems = filtered.filter((i) => bucket.test(i.rul_days))
          if (bucketItems.length === 0) return null
          return (
            <div key={bucket.key} className="rounded-xl border border-line bg-surface shadow-card overflow-hidden">
              <div className="flex items-center gap-2 px-5 py-3 border-b border-line bg-surface-sunken/40">
                <CalendarClock size={14} className="text-ink-faint" />
                <h3 className="font-semibold text-ink text-xs uppercase tracking-wide">{bucket.label}</h3>
                <span className="text-xs text-ink-faint">({bucketItems.length})</span>
              </div>
              <table className="w-full text-sm">
                <tbody>
                  {bucketItems.map((item) => (
                    <tr
                      key={`${item.vin}-${item.part_code}`}
                      onClick={() => navigate(`/failure-probability?vin=${item.vin}`)}
                      className="border-t border-line first:border-t-0 cursor-pointer hover:bg-surface-sunken/60 transition-colors"
                    >
                      <td className="px-5 py-3 font-medium text-ink text-xs whitespace-nowrap">{item.vin}</td>
                      <td className="px-5 py-3 text-ink-dim text-xs">{item.model}</td>
                      <td className="px-5 py-3 text-ink text-xs font-semibold">{item.part_name}</td>
                      <td className="px-5 py-3">
                        <RiskBadge tier={item.risk_tier} />
                      </td>
                      <td className="px-5 py-3 text-xs text-ink-faint text-right">{pct(item.failure_probability)}</td>
                      <td className="px-5 py-3 text-right font-bold text-ink tabular-nums whitespace-nowrap">
                        {item.rul_days} days
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        })}
      </div>
    </div>
  )
}
