import { RISK_COLORS } from '../constants'

function polarToCartesian(cx, cy, r, angleDeg) {
  const rad = ((angleDeg - 90) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle)
  const end = polarToCartesian(cx, cy, r, startAngle)
  const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1'
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`
}

const START_ANGLE = -135
const SWEEP = 270

/**
 * SignalArc — the product's signature element. A 270deg radial gauge, the
 * same visual language as the vehicle sensor gauges (coolant temp, oil
 * pressure) this whole product reads — used everywhere a probability is
 * shown instead of a generic progress bar.
 */
export default function SignalArc({ value, tier, size = 88, strokeWidth = 9, label, sublabel }) {
  const clamped = Math.max(0, Math.min(1, value))
  const cx = size / 2
  const cy = size / 2
  const r = size / 2 - strokeWidth
  const trackPath = describeArc(cx, cy, r, START_ANGLE, START_ANGLE + SWEEP)
  const valuePath = describeArc(cx, cy, r, START_ANGLE, START_ANGLE + SWEEP * clamped)
  const color = RISK_COLORS[tier]?.fill || '#A69C87'

  return (
    <div className="inline-flex flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <path d={trackPath} fill="none" stroke="#F6D9C3" strokeWidth={strokeWidth} strokeLinecap="round" />
        <path
          d={valuePath}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          style={{ transition: 'all 0.4s ease' }}
        />
        <text
          x="50%"
          y="47%"
          textAnchor="middle"
          dominantBaseline="middle"
          className="font-extrabold fill-ink tabular-nums"
          style={{ fontSize: size * 0.22 }}
        >
          {label ?? `${Math.round(clamped * 100)}%`}
        </text>
        {sublabel && (
          <text
            x="50%"
            y="66%"
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-ink-faint font-medium uppercase tracking-wide"
            style={{ fontSize: size * 0.095 }}
          >
            {sublabel}
          </text>
        )}
      </svg>
    </div>
  )
}
