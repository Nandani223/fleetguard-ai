import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { getMaintenanceCalendar } from '../api/client'
import { listParts } from '../api/client'
import Loading from '../components/Loading'
import EmptyState from '../components/EmptyState'

function formatMoney(n) {
  return n.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

export default function CostImpactPage() {
  const [items, setItems] = useState(null)
  const [parts, setParts] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  // category -> assumed $ avoided per Red-tier vehicle caught early.
  // Starts at 0 for every category on purpose — these are NOT derived
  // from any data in this app, unlike every other number on screen, so
  // nothing here should look pre-filled with authority.
  const [assumptions, setAssumptions] = useState({})

  useEffect(() => {
    setLoading(true)
    Promise.all([getMaintenanceCalendar(), listParts()])
      .then(([cal, partList]) => {
        setItems(cal.items)
        setParts(partList)
        const categories = [...new Set(partList.map((p) => p.category))]
        setAssumptions(Object.fromEntries(categories.map((c) => [c, 0])))
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const categoryMap = useMemo(() => {
    if (!parts) return {}
    return Object.fromEntries(parts.map((p) => [p.part_code, p.category]))
  }, [parts])

  const byCategory = useMemo(() => {
    if (!items) return []
    const grouped = {}
    for (const item of items) {
      const category = categoryMap[item.part_code] || 'Other'
      if (!grouped[category]) grouped[category] = { category, red: 0, amber: 0, green: 0 }
      grouped[category][item.risk_tier.toLowerCase()] += 1
    }
    return Object.values(grouped).sort((a, b) => b.red - a.red)
  }, [items, categoryMap])

  const totalAvoided = byCategory.reduce(
    (sum, row) => sum + row.red * (assumptions[row.category] || 0),
    0
  )
  const totalRed = byCategory.reduce((sum, row) => sum + row.red, 0)

  if (loading) return <Loading label="Loading fleet data" />
  if (error) return <EmptyState title="Couldn't load cost data" body={error} />
  if (!items || items.length === 0) {
    return (
      <EmptyState
        title="No RUL data yet"
        body="This page counts real Red-tier vehicles from RUL Explorer's data. Run scoring and RUL for at least one part first."
      />
    )
  }

  return (
    <div className="max-w-4xl">
      <div className="flex items-start gap-2.5 p-4 rounded-xl bg-risk-amber-soft text-risk-amber mb-5">
        <AlertTriangle size={16} className="shrink-0 mt-0.5" />
        <p className="text-sm">
          <span className="font-semibold">Vehicle counts below are real</span> — pulled straight from RUL
          Explorer's live data. <span className="font-semibold">The dollar figures are not</span> — they only
          exist because of the cost-per-catch numbers you enter below. Nobody has measured what a failure
          actually costs your fleet yet, so treat this page as a calculator you drive, not a report.
        </p>
      </div>

      <div className="rounded-xl border border-line bg-surface shadow-card p-5 mb-5">
        <p className="text-xs text-ink-faint uppercase tracking-wide font-semibold mb-1">
          Estimated Cost Avoided
        </p>
        <p className="text-3xl font-extrabold text-ink tabular-nums">{formatMoney(totalAvoided)}</p>
        <p className="text-xs text-ink-dim mt-1">
          Based on {totalRed} Red-tier vehicle{totalRed === 1 ? '' : 's'} across all parts, at the per-category
          rates you set below.
        </p>
      </div>

      <div className="rounded-xl border border-line bg-surface shadow-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-surface-sunken text-ink-faint text-xs uppercase tracking-wide">
              <th className="text-left px-5 py-2.5 font-semibold">Category</th>
              <th className="text-right px-5 py-2.5 font-semibold">Red</th>
              <th className="text-right px-5 py-2.5 font-semibold">Amber</th>
              <th className="text-right px-5 py-2.5 font-semibold">Green</th>
              <th className="text-right px-5 py-2.5 font-semibold w-52">$ Avoided / Red Catch</th>
              <th className="text-right px-5 py-2.5 font-semibold">Subtotal</th>
            </tr>
          </thead>
          <tbody>
            {byCategory.map((row) => (
              <tr key={row.category} className="border-t border-line">
                <td className="px-5 py-3 font-medium text-ink">{row.category}</td>
                <td className="px-5 py-3 text-right text-risk-red font-bold tabular-nums">{row.red}</td>
                <td className="px-5 py-3 text-right text-risk-amber tabular-nums">{row.amber}</td>
                <td className="px-5 py-3 text-right text-risk-green tabular-nums">{row.green}</td>
                <td className="px-5 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <span className="text-ink-faint text-xs">$</span>
                    <input
                      type="number"
                      min="0"
                      step="100"
                      value={assumptions[row.category] ?? 0}
                      onChange={(e) =>
                        setAssumptions((prev) => ({ ...prev, [row.category]: Number(e.target.value) || 0 }))
                      }
                      className="w-24 bg-surface-sunken border border-line rounded-lg px-2 py-1.5 text-sm text-ink text-right focus:outline-none focus:border-brand"
                    />
                  </div>
                </td>
                <td className="px-5 py-3 text-right font-bold text-ink tabular-nums">
                  {formatMoney(row.red * (assumptions[row.category] || 0))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
