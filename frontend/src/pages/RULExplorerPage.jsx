import { useEffect, useState } from 'react'
import { RefreshCw, Mail, CheckCircle2, XCircle } from 'lucide-react'
import { useParts } from '../hooks/usePartContext'
import { listPredictions, runRul, getRul, getPredictionDetail, draftOutreach } from '../api/client'
import RiskBadge from '../components/RiskBadge'
import Loading from '../components/Loading'
import EmptyState from '../components/EmptyState'
import SignalArc from '../components/SignalArc'
import RulComparisonChart from '../components/RulComparisonChart'

function SectionBadge({ n }) {
  return (
    <span className="inline-flex items-center justify-center w-5 h-5 rounded bg-brand-soft text-brand-dim text-[11px] font-bold shrink-0">
      {n}
    </span>
  )
}

export default function RULExplorerPage() {
  const { selectedPartCode, selectedPart } = useParts()
  const [predictions, setPredictions] = useState([])
  const [selectedVin, setSelectedVin] = useState(null)
  const [probDetail, setProbDetail] = useState(null)
  const [rulDetail, setRulDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [running, setRunning] = useState(false)

  const [draft, setDraft] = useState(null)
  const [draftLoading, setDraftLoading] = useState(false)
  const [draftText, setDraftText] = useState('')

  useEffect(() => {
    if (!selectedPartCode) return
    setLoading(true)
    setError(null)
    setSelectedVin(null)
    setProbDetail(null)
    setRulDetail(null)
    setDraft(null)
    listPredictions(selectedPartCode)
      .then((data) => {
        setPredictions(data)
        if (data.length > 0) {
          const preferred = data.find((p) => p.risk_tier === 'Red') || data[0]
          loadVinDetail(preferred.vin)
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPartCode])

  async function loadVinDetail(vin) {
    setSelectedVin(vin)
    setDraft(null)
    try {
      const [prob, rul] = await Promise.all([
        getPredictionDetail(vin, selectedPartCode),
        getRul(vin, selectedPartCode),
      ])
      setProbDetail(prob)
      setRulDetail(rul)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleRunRul() {
    setRunning(true)
    try {
      await runRul(selectedPartCode)
      if (selectedVin) await loadVinDetail(selectedVin)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  async function handleDraft() {
    setDraftLoading(true)
    setDraft(null)
    try {
      const result = await draftOutreach(selectedVin, selectedPartCode)
      setDraft(result)
      setDraftText(result.draft || '')
    } catch (err) {
      setDraft({ error: err.message })
    } finally {
      setDraftLoading(false)
    }
  }

  const runButton = (
    <button
      onClick={handleRunRul}
      disabled={running || predictions.length === 0}
      className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-brand text-white text-sm font-semibold hover:brightness-110 transition-all disabled:opacity-40 shadow-pop"
    >
      <RefreshCw size={14} className={running ? 'animate-spin' : ''} />
      {running ? 'Computing…' : 'Run RUL for this part'}
    </button>
  )

  if (loading) return <Loading label="Loading predictions" />

  if (predictions.length === 0) {
    return (
      <EmptyState
        title="No predictions yet"
        body={`Run scoring for ${selectedPart?.part_name} on the Failure Probability screen first, then RUL can be computed against it.`}
      />
    )
  }

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2.5">
          <span className="text-xs text-ink-faint uppercase tracking-wide font-semibold">Vehicle</span>
          <select
            value={selectedVin || ''}
            onChange={(e) => loadVinDetail(e.target.value)}
            className="bg-surface-sunken border border-line rounded-lg px-3.5 py-2 text-sm font-medium text-ink focus:outline-none focus:border-brand"
          >
            {predictions.map((p) => (
              <option key={p.vin} value={p.vin}>
                {p.vin} — {p.risk_tier}
              </option>
            ))}
          </select>
        </div>
        {runButton}
      </div>

      {probDetail && rulDetail && (
        <>
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl border border-line bg-surface shadow-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <SectionBadge n="01" />
                <p className="text-xs text-ink-faint uppercase tracking-wide font-semibold">Failure Probability</p>
              </div>
              <div className="flex justify-center mb-3">
                <SignalArc value={probDetail.failure_probability} tier={probDetail.risk_tier} size={110} strokeWidth={9} />
              </div>
              <div className="flex justify-center">
                <RiskBadge tier={probDetail.risk_tier} />
              </div>
            </div>

            <div className="rounded-xl border border-line bg-surface shadow-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <SectionBadge n="02" />
                <p className="text-xs text-ink-faint uppercase tracking-wide font-semibold">Remaining Useful Life</p>
              </div>
              <div className="flex flex-col items-center justify-center h-[110px]">
                <span className="text-4xl font-extrabold text-ink tabular-nums">{rulDetail.rul_days}</span>
                <span className="text-xs text-ink-dim mt-1">days ({rulDetail.rul_km.toLocaleString()} km)</span>
              </div>
              <div className="flex justify-center">
                <RiskBadge tier={rulDetail.risk_tier} />
              </div>
            </div>
          </div>

          <div
            className={`mt-4 flex items-start gap-2.5 p-3.5 rounded-xl text-sm ${
              rulDetail.consistent ? 'bg-risk-green-soft text-risk-green' : 'bg-risk-amber-soft text-risk-amber'
            }`}
          >
            {rulDetail.consistent ? (
              <CheckCircle2 size={16} className="shrink-0 mt-0.5" />
            ) : (
              <XCircle size={16} className="shrink-0 mt-0.5" />
            )}
            <span className="font-medium">{rulDetail.consistency_note}</span>
          </div>

          <div className="mt-4 rounded-xl border border-line bg-surface shadow-card p-5">
            <div className="flex items-center gap-2 mb-3">
              <SectionBadge n="03" />
              <p className="text-xs text-ink-faint uppercase tracking-wide font-semibold">
                Baseline vs. Risk-Adjusted RUL
              </p>
            </div>
            <RulComparisonChart
              baselineDays={rulDetail.baseline_remaining_days}
              adjustedDays={rulDetail.rul_days}
              tier={rulDetail.risk_tier}
            />
          </div>

          <div className="mt-4 pt-6 border-t border-line">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <SectionBadge n="04" />
                <p className="text-sm font-semibold text-ink">Action Agent</p>
              </div>
              <button
                onClick={handleDraft}
                disabled={draftLoading}
                className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-brand-soft text-brand-dim text-sm font-semibold hover:bg-brand/20 transition-colors disabled:opacity-40"
              >
                <Mail size={14} />
                {draftLoading ? 'Drafting…' : 'Draft Outreach Message'}
              </button>
            </div>
            {draft && draft.error && (
              <p className="text-sm text-risk-amber bg-risk-amber-soft rounded-lg p-3">{draft.error}</p>
            )}
            {draft && draft.draft && (
              <div>
                <textarea
                  value={draftText}
                  onChange={(e) => setDraftText(e.target.value)}
                  rows={6}
                  className="w-full bg-surface-sunken border border-line rounded-lg p-3.5 text-sm text-ink leading-relaxed focus:outline-none focus:border-brand resize-y"
                />
                <p className="text-xs text-ink-faint mt-2">
                  Draft only — nothing is sent automatically. Edit freely, then copy/send it yourself.
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
