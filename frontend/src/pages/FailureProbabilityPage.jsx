import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { useParts } from '../hooks/usePartContext'
import { listPredictions, runPredictions, getPredictionDetail } from '../api/client'
import { pct } from '../constants'
import SignalArc from '../components/SignalArc'
import RiskBadge from '../components/RiskBadge'
import TrendLineChart from '../components/TrendLineChart'
import ContributionBarChart from '../components/ContributionBarChart'
import Loading from '../components/Loading'
import EmptyState from '../components/EmptyState'

const TIERS = ['All', 'Red', 'Amber', 'Green']

function SectionBadge({ n }) {
  return (
    <span className="inline-flex items-center justify-center w-5 h-5 rounded bg-brand-soft text-brand-dim text-[11px] font-bold shrink-0">
      {n}
    </span>
  )
}

function StatCard({ label, value, tone }) {
  const toneClass = {
    default: 'text-ink',
    red: 'text-risk-red',
    amber: 'text-risk-amber',
    green: 'text-risk-green',
  }[tone || 'default']
  return (
    <div className="flex-1 rounded-xl border border-line bg-surface shadow-card px-4 py-3.5">
      <p className="text-xs text-ink-faint uppercase tracking-wide font-semibold mb-1">{label}</p>
      <p className={`text-2xl font-extrabold tabular-nums ${toneClass}`}>{value}</p>
    </div>
  )
}

export default function FailureProbabilityPage() {
  const { selectedPartCode, selectedPart } = useParts()
  const [predictions, setPredictions] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [tier, setTier] = useState('All')
  const [running, setRunning] = useState(false)
  const [selectedVin, setSelectedVin] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [allPredictions, setAllPredictions] = useState(null)

  function load() {
    if (!selectedPartCode) return
    setLoading(true)
    setError(null)
    listPredictions(selectedPartCode, tier === 'All' ? undefined : tier, 500)
      .then(setPredictions)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
    listPredictions(selectedPartCode, undefined, 500).then(setAllPredictions).catch(() => setAllPredictions(null))
  }

  useEffect(() => {
    load()
    setSelectedVin(null)
    setDetail(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPartCode, tier])

  async function handleRun() {
    setRunning(true)
    setError(null)
    try {
      await runPredictions(selectedPartCode)
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  async function handleSelectVin(vin) {
    setSelectedVin(vin)
    setDetailLoading(true)
    try {
      const d = await getPredictionDetail(vin, selectedPartCode)
      setDetail(d)
    } catch (err) {
      setDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }

  const runButton = (
    <button
      onClick={handleRun}
      disabled={running}
      className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-brand text-white text-sm font-semibold hover:brightness-110 transition-all disabled:opacity-40 shadow-pop"
    >
      <RefreshCw size={14} className={running ? 'animate-spin' : ''} />
      {running ? 'Scoring…' : 'Run Scoring'}
    </button>
  )

  const tierCounts = allPredictions
    ? { Red: 0, Amber: 0, Green: 0, ...Object.fromEntries(['Red', 'Amber', 'Green'].map((t) => [t, allPredictions.filter((p) => p.risk_tier === t).length])) }
    : null

  return (
    <div>
      {tierCounts && (allPredictions?.length ?? 0) > 0 && (
        <div className="flex gap-3 mb-5">
          <StatCard label="Total Tracked" value={allPredictions.length} />
          <StatCard label="Red Tier" value={tierCounts.Red} tone="red" />
          <StatCard label="Amber Tier" value={tierCounts.Amber} tone="amber" />
          <StatCard label="Green Tier" value={tierCounts.Green} tone="green" />
        </div>
      )}

      <div className="flex gap-6">
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-4">
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
            {runButton}
          </div>

          {loading && <Loading label="Loading predictions" />}
          {!loading && error && <EmptyState title="No scoring run found" body={error} action={runButton} />}
          {!loading && !error && predictions && predictions.length === 0 && (
            <EmptyState
              title={tier === 'All' ? 'No predictions yet' : `No ${tier}-tier vehicles`}
              body={
                tier === 'All'
                  ? `Run the scoring engine to compute live failure probabilities for ${selectedPart?.part_name}.`
                  : `Every vehicle for ${selectedPart?.part_name} is outside the ${tier} tier right now — that's a good thing.`
              }
              action={tier === 'All' ? runButton : undefined}
            />
          )}

          {!loading && predictions && predictions.length > 0 && (
            <div className="rounded-xl border border-line bg-surface shadow-card overflow-hidden">
              <div className="flex items-center gap-2 px-5 py-4 border-b border-line">
                <SectionBadge n="01" />
                <h2 className="font-semibold text-ink text-sm">
                  Vehicles ranked by failure probability — {selectedPart?.part_name}
                </h2>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-surface-sunken text-ink-faint text-xs uppercase tracking-wide">
                    <th className="text-left px-5 py-2.5 font-semibold">VIN</th>
                    <th className="text-left px-5 py-2.5 font-semibold">Risk</th>
                    <th className="text-right px-5 py-2.5 font-semibold">Probability</th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.map((p) => (
                    <tr
                      key={p.vin}
                      onClick={() => handleSelectVin(p.vin)}
                      className={`border-t border-line cursor-pointer transition-colors ${
                        selectedVin === p.vin ? 'bg-brand-soft' : 'hover:bg-surface-sunken/60'
                      }`}
                    >
                      <td className="px-5 py-3 font-medium text-ink text-xs whitespace-nowrap">{p.vin}</td>
                      <td className="px-5 py-3">
                        <RiskBadge tier={p.risk_tier} />
                      </td>
                      <td className="px-5 py-3 text-right font-bold text-ink tabular-nums">
                        {pct(p.failure_probability)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="w-96 shrink-0">
          {!selectedVin && (
            <EmptyState title="Select a vehicle" body="Pick a row to see its full risk profile and trend." />
          )}
          {selectedVin && detailLoading && <Loading label="Loading detail" />}
          {selectedVin && !detailLoading && detail && (
            <div className="rounded-xl border border-line bg-surface shadow-card p-5 sticky top-0">
              <p className="text-xs font-semibold text-ink-faint mb-3">{detail.vin}</p>
              <div className="flex justify-center mb-4">
                <SignalArc value={detail.failure_probability} tier={detail.risk_tier} size={120} strokeWidth={10} />
              </div>
              <div className="flex justify-center mb-5">
                <RiskBadge tier={detail.risk_tier} />
              </div>

              <div className="mb-5">
                <p className="text-xs text-ink-faint uppercase tracking-wide font-semibold mb-2">
                  Which Signals Drive This Prediction
                </p>
                {detail.top_signal_contributions && detail.top_signal_contributions.length > 0 ? (
                  <ContributionBarChart contributions={detail.top_signal_contributions} tier={detail.risk_tier} />
                ) : (
                  <p className="text-xs text-ink-dim italic">No signal strong enough to explain this score.</p>
                )}
              </div>

              <div className="mb-3">
                <p className="text-xs text-ink-faint uppercase tracking-wide font-semibold mb-2">
                  Probability Trend, Last 6 Weeks
                </p>
                <TrendLineChart values={detail.trend} tier={detail.risk_tier} />
              </div>

              {detail.estimated_window_days != null && (
                <div className="mt-2 pt-4 border-t border-line flex items-center justify-between">
                  <p className="text-xs text-ink-faint uppercase tracking-wide font-semibold">Estimated Window</p>
                  <p className="text-sm font-bold text-ink tabular-nums">{detail.estimated_window_days} days</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
