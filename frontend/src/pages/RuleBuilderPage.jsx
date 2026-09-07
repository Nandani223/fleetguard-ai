import { useEffect, useState } from 'react'
import { Check, Save, AlertCircle } from 'lucide-react'
import { useParts } from '../hooks/usePartContext'
import { getCorrelation, buildRule } from '../api/client'
import { signalLabel } from '../constants'
import Loading from '../components/Loading'
import EmptyState from '../components/EmptyState'
import CorrelationBarChart from '../components/CorrelationBarChart'

const METHODS = [
  { id: 'point_biserial', label: 'Point-Biserial' },
  { id: 'xgboost_importance', label: 'XGBoost Importance' },
]

function SectionBadge({ n }) {
  return (
    <span className="inline-flex items-center justify-center w-5 h-5 rounded bg-brand-soft text-brand-dim text-[11px] font-bold shrink-0">
      {n}
    </span>
  )
}

export default function RuleBuilderPage() {
  const { selectedPartCode, selectedPart } = useParts()
  const [correlation, setCorrelation] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [method, setMethod] = useState('point_biserial')
  const [included, setIncluded] = useState({})
  const [saving, setSaving] = useState(false)
  const [savedRule, setSavedRule] = useState(null)

  useEffect(() => {
    if (!selectedPartCode) return
    setLoading(true)
    setError(null)
    setSavedRule(null)
    getCorrelation(selectedPartCode)
      .then((data) => {
        setCorrelation(data)
        const defaults = {}
        data.signals.forEach((s) => {
          defaults[s.signal] = Math.abs(s.point_biserial_r) > 0.08
        })
        setIncluded(defaults)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [selectedPartCode])

  async function handleSave() {
    setSaving(true)
    try {
      const signals = correlation.signals.map((s) => ({
        signal: s.signal,
        included: !!included[s.signal],
      }))
      const result = await buildRule(selectedPartCode, method, signals)
      setSavedRule(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Loading label="Computing signal correlations" />
  if (error) return <EmptyState title="Couldn't compute correlations" body={error} />
  if (!correlation) return null

  const nIncluded = Object.values(included).filter(Boolean).length
  const maxAbs = Math.max(...correlation.signals.map((s) => Math.abs(s.point_biserial_r)), 0.01)

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-ink-dim">
          <span className="font-semibold text-ink">{correlation.n_failed}</span> failed ·{' '}
          <span className="font-semibold text-ink">{correlation.n_not_failed}</span> not-failed vehicles analyzed
        </p>
        <div className="flex bg-surface-sunken rounded-lg p-1">
          {METHODS.map((m) => (
            <button
              key={m.id}
              onClick={() => setMethod(m.id)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                method === m.id ? 'bg-surface text-brand-dim shadow-sm' : 'text-ink-dim hover:text-ink'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-line bg-surface shadow-card p-5 mb-5">
        <div className="flex items-center gap-2 mb-1">
          <SectionBadge n="01" />
          <h2 className="font-semibold text-ink text-sm">
            Signal correlation — {selectedPart?.part_name}
          </h2>
        </div>
        <p className="text-xs text-ink-dim mb-3 ml-7">
          Telematics signals correlated against failure history. Muted bars fall below the
          inclusion threshold (|r| &lt; 0.08).
        </p>
        <CorrelationBarChart signals={correlation.signals} />
      </div>

      <div className="rounded-xl border border-line bg-surface shadow-card p-5 mb-5">
        <div className="flex items-center gap-2 mb-4">
          <SectionBadge n="02" />
          <h2 className="font-semibold text-ink text-sm">Build the rule</h2>
        </div>
        <p className="text-xs text-ink-dim mb-4 ml-7">
          Uncheck any signal to exclude it — weights automatically renormalize among what's included.
        </p>

        <div className="rounded-lg border border-line overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-sunken text-ink-faint text-xs uppercase tracking-wide">
                <th className="text-left px-4 py-2.5 font-semibold">Include</th>
                <th className="text-left px-4 py-2.5 font-semibold">Signal</th>
                <th className="text-right px-4 py-2.5 font-semibold">Point-Biserial r</th>
                <th className="text-right px-4 py-2.5 font-semibold">XGBoost Importance</th>
              </tr>
            </thead>
            <tbody>
              {correlation.signals.map((s) => (
                <tr key={s.signal} className="border-t border-line hover:bg-surface-sunken/60 transition-colors">
                  <td className="px-4 py-3">
                    <button
                      onClick={() => setIncluded((prev) => ({ ...prev, [s.signal]: !prev[s.signal] }))}
                      className={`w-5 h-5 rounded-md border flex items-center justify-center transition-colors ${
                        included[s.signal]
                          ? 'bg-brand border-brand text-white'
                          : 'border-line text-transparent hover:border-brand/50'
                      }`}
                    >
                      <Check size={13} strokeWidth={3} />
                    </button>
                  </td>
                  <td className="px-4 py-3 text-ink font-medium">{signalLabel(s.signal)}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 h-1.5 rounded-full bg-surface-sunken overflow-hidden">
                        <div
                          className="h-full bg-brand rounded-full"
                          style={{ width: `${(Math.abs(s.point_biserial_r) / maxAbs) * 100}%` }}
                        />
                      </div>
                      <span
                        className={`tabular-nums w-14 text-right ${
                          Math.abs(s.point_biserial_r) > 0.08 ? 'text-ink font-semibold' : 'text-ink-faint'
                        }`}
                      >
                        {s.point_biserial_r > 0 ? '+' : ''}
                        {s.point_biserial_r.toFixed(3)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-ink-dim">
                    {s.xgboost_importance.toFixed(3)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-5 flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving || nIncluded === 0}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand text-white text-sm font-semibold hover:brightness-110 transition-all disabled:opacity-40 shadow-pop"
          >
            <Save size={15} />
            {saving ? 'Saving…' : `Save Rule (${nIncluded} signal${nIncluded === 1 ? '' : 's'})`}
          </button>
          {nIncluded === 0 && (
            <span className="flex items-center gap-1.5 text-xs text-risk-amber font-medium">
              <AlertCircle size={13} />
              No signals included — {selectedPart?.part_name} will score at its historical base rate
            </span>
          )}
        </div>

        {savedRule && (
          <div className="mt-5 p-4 rounded-xl bg-risk-green-soft border border-risk-green/20">
            <p className="text-sm text-risk-green font-semibold mb-2.5">
              Rule saved for {selectedPart?.part_name} ({savedRule.method})
            </p>
            <div className="flex flex-wrap gap-2">
              {savedRule.signals
                .filter((s) => s.included)
                .map((s) => (
                  <span
                    key={s.signal}
                    className="text-xs font-medium px-2.5 py-1.5 rounded-lg bg-surface border border-line text-ink-dim tabular-nums"
                  >
                    {signalLabel(s.signal)} · {s.weight.toFixed(3)}
                  </span>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
