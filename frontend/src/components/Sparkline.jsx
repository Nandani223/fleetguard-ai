const COLOR_MAP = { Green: '#16A34A', Amber: '#D97706', Red: '#E5484D' }

export default function Sparkline({ values, tier, width = 100, height = 28 }) {
  if (!values || values.length < 2) {
    return <div style={{ width, height }} className="flex items-center text-ink-faint text-xs">—</div>
  }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const stepX = width / (values.length - 1)

  const points = values
    .map((v, i) => {
      const x = i * stepX
      const y = height - ((v - min) / range) * (height - 4) - 2
      return `${x},${y}`
    })
    .join(' ')

  const color = COLOR_MAP[tier] || '#A69C87'

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}
