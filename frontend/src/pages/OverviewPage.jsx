import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { SlidersHorizontal, Gauge, BatteryWarning, ArrowRight } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useParts } from '../hooks/usePartContext'
import { getCorrelation, listPredictions } from '../api/client'
import { signalLabel, TELEMATICS_SIGNALS } from '../constants'
import Loading from '../components/Loading'

function SectionBadge({ n }) {
  return (
    <span className="inline-flex items-center justify-center w-5 h-5 rounded bg-brand-soft text-brand-dim text-[11px] font-bold shrink-0">
      {n}
    </span>
  )
}

function StatCard({ label, value, tone, icon: Icon }) {
  const toneClass = { default: 'text-ink', red: 'text-risk-red', amber: 'text-risk-amber', green: 'text-risk-green' }[tone || 'default']
  return (
    <div className="flex-1 rounded-xl border border-line bg-surface shadow-card px-5 py-4">
      <div className="flex items-center gap-2 mb-2">
        {Icon && <Icon size={14} className="text-ink-faint" />}
        <p className="text-xs text-ink-faint uppercase tracking-wide font-semibold">{label}</p>
      </div>
      <p className={`text-3xl font-extrabold tabular-nums ${toneClass}`}>{value}</p>
    </div>
  )
}

const NAV_CARDS = [
  {
    to: '/rule-builder',
    icon: SlidersHorizontal,
    title: 'Open Failure Probability Rule Builder',
    body: 'Select a part, review fleet history, correlate telematics signals, and deploy a scoring rule.',
  },
  {
    to: '/failure-probability',
    icon: Gauge,
    title: 'Open Failure Probability',
    body: 'Ranked by VIN — pick a vehicle, check failure probability for every part tracked on it, with the precursor signals driving each score.',
  },
  {
    to: '/rul-explorer',
    icon: BatteryWarning,
    title: 'Open RUL Explorer',
    body: 'Ranked by VIN — check remaining useful life for every part tracked on it, with the degradation curve behind each estimate.',
  },
]

export default function OverviewPage() {
  const { parts } = useParts()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState(null)
  const [fleetSignals, setFleetSignals] = useState([])

  useEffect(() => {
    if (!parts || parts.length === 0) return
    let cancelled = false
    setLoading(true)
    setError(null)

    async function load() {
      try {
        const results = await Promise.all(
          parts.map(async (p) => {
            const [corr, preds] = await Promise.all([
              getCorrelation(p.part_code).catch(() => null),
              listPredictions(p.part_code, undefined, 500).catch(() => []),
            ])
            return { part: p, corr, preds }
          })
        )
        if (cancelled) return

        let totalScored = 0, totalRed = 0, totalAmber = 0
        let partsWithSignal = 0
        const signalSums = Object.fromEntries(TELEMATICS_SIGNALS.map((s) => [s, { sum: 0, n: 0 }]))

        for (const { corr, preds } of results) {
          totalScored += preds.length
          totalRed += preds.filter((p) => p.risk_tier === 'Red').length
          totalAmber += preds.filter((p) => p.risk_tier === 'Amber').length
          if (corr) {
            const maxAbs = Math.max(...corr.signals.map((s) => Math.abs(s.point_biserial_r)), 0)
            if (maxAbs > 0.08) partsWithSignal += 1
            corr.signals.forEach((s) => {
              signalSums[s.signal].sum += Math.abs(s.point_biserial_r)
              signalSums[s.signal].n += 1
            })
          }
        }

        const fleetSignalData = TELEMATICS_SIGNALS.map((s) => ({
          name: signalLabel(s),
          magnitude: signalSums[s].n ? Math.round((signalSums[s].sum / signalSums[s].n) * 1000) / 10 : 0,
        })).sort((a, b) => b.magnitude - a.magnitude)

        setStats({
          totalScored, totalRed, totalAmber,
          partsWithSignal, totalParts: parts.length,
        })
        setFleetSignals(fleetSignalData)
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [parts])

  if (loading) return <Loading label="Aggregating fleet-wide signal patterns" />
  if (error) return <p className="text-sm text-risk-red">{error}</p>
  if (!stats) return null

  return (
    <div>
      <div className="flex gap-4 mb-6">
        <StatCard label="Components Under Watch" value={stats.totalScored} icon={Gauge} />
        <StatCard label="High Failure Probability" value={stats.totalRed} tone="red" icon={SlidersHorizontal} />
        <StatCard label="Elevated Risk (Amber)" value={stats.totalAmber} tone="amber" icon={BatteryWarning} />
        <StatCard
          label="Parts With Validated Signal"
          value={`${stats.partsWithSignal} / ${stats.totalParts}`}
          icon={Gauge}
        />
      </div>

      <div className="rounded-xl border border-line bg-surface shadow-card p-5 mb-6">
        <div className="flex items-center gap-2 mb-1">
          <SectionBadge n="01" />
          <h2 className="font-semibold text-ink text-sm">Top Precursor Signals Across the Fleet</h2>
        </div>
        <p className="text-xs text-ink-dim mb-3 ml-7">
          Average correlation magnitude per telematics signal, across all {stats.totalParts} tracked parts.
        </p>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={fleetSignals} layout="vertical" margin={{ top: 4, right: 24, left: 4, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#EBE3D0" horizontal={false} />
            <XAxis
              type="number"
              domain={[0, 'dataMax']}
              tickFormatter={(v) => `${v}%`}
              tick={{ fill: '#A69C87', fontSize: 11 }}
              axisLine={{ stroke: '#EBE3D0' }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={150}
              tick={{ fill: '#211E17', fontSize: 12 }}
              axisLine={{ stroke: '#EBE3D0' }}
              tickLine={false}
            />
            <Tooltip
              formatter={(v) => [`${v}% avg |r|`, 'Signal strength']}
              contentStyle={{ borderRadius: 8, border: '1px solid #EBE3D0', fontSize: 12 }}
            />
            <Bar dataKey="magnitude" fill="#E1794B" radius={[0, 4, 4, 0]} maxBarSize={16} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {NAV_CARDS.map((card) => (
          <Link
            key={card.to}
            to={card.to}
            className="group rounded-xl border border-line bg-surface shadow-card p-5 hover:border-brand/40 transition-colors"
          >
            <div className="w-9 h-9 rounded-lg bg-brand-soft flex items-center justify-center mb-3">
              <card.icon size={16} className="text-brand-dim" />
            </div>
            <h3 className="font-semibold text-ink text-sm mb-1.5">{card.title}</h3>
            <p className="text-xs text-ink-dim leading-relaxed mb-3">{card.body}</p>
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-brand-dim">
              Open <ArrowRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}
