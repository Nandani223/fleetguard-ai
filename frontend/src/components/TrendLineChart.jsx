import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

const COLOR_MAP = { Green: '#16A34A', Amber: '#D97706', Red: '#E5484D' }

export default function TrendLineChart({ values, tier, redThreshold = 0.6 }) {
  const n = values.length
  const data = values.map((v, i) => ({
    week: i === n - 1 ? 'Now' : `W-${n - 1 - i}`,
    probability: Math.round(v * 1000) / 10,
  }))
  const color = COLOR_MAP[tier] || '#A69C87'

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: -12, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#EBE3D0" vertical={false} />
        <XAxis dataKey="week" tick={{ fill: '#A69C87', fontSize: 11 }} axisLine={{ stroke: '#EBE3D0' }} tickLine={false} />
        <YAxis
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
          tick={{ fill: '#A69C87', fontSize: 11 }}
          axisLine={{ stroke: '#EBE3D0' }}
          tickLine={false}
        />
        <ReferenceLine
          y={redThreshold * 100}
          stroke="#E5484D"
          strokeDasharray="4 4"
          label={{ value: 'Red threshold', position: 'insideTopRight', fill: '#E5484D', fontSize: 10 }}
        />
        <Tooltip
          formatter={(v) => [`${v}%`, 'Failure probability']}
          contentStyle={{ borderRadius: 8, border: '1px solid #EBE3D0', fontSize: 12 }}
        />
        <Line
          type="monotone"
          dataKey="probability"
          stroke={color}
          strokeWidth={2.5}
          dot={{ r: 3, fill: color, strokeWidth: 0 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
