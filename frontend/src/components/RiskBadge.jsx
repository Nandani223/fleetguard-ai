import { AlertTriangle, AlertCircle, CheckCircle2 } from 'lucide-react'
import { RISK_COLORS } from '../constants'

const ICONS = { Green: CheckCircle2, Amber: AlertCircle, Red: AlertTriangle }

export default function RiskBadge({ tier }) {
  const c = RISK_COLORS[tier] || RISK_COLORS.Green
  const Icon = ICONS[tier] || CheckCircle2
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wide ${c.text} ${c.bg}`}
    >
      <Icon size={12} strokeWidth={2.5} />
      {tier}
    </span>
  )
}
