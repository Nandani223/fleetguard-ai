import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { signalLabel } from '../constants'

const COLOR_MAP = { Green: '#16A34A', Amber: '#D97706', Red: '#E5484D' }

/** Real bar chart of each top signal's actual contribution to this
 * vehicle's score (weight * z-score, from the live scoring engine —
 * app/services/scoring.py's `contributions` dict), not equal-width
 * placeholder bars. */
export default function ContributionBarChart({ contributions, tier }) {
  if (!contributions || contributions.length === 0) return null
  const color = COLOR_MAP[tier] || '#E1794B'
  const data = contributions.map((c) => ({
    name: signalLabel(c.signal),
    value: Math.round(c.contribution * 1000) / 1000,
  }))

  return (
    <ResponsiveContainer width="100%" height={110}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 20, left: 4, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#EBE3D0" horizontal={false} />
        <XAxis type="number" tick={{ fill: '#A69C87', fontSize: 10 }} axisLine={{ stroke: '#EBE3D0' }} tickLine={false} />
        <YAxis
          type="category"
          dataKey="name"
          width={120}
          tick={{ fill: '#211E17', fontSize: 11 }}
          axisLine={{ stroke: '#EBE3D0' }}
          tickLine={false}
        />
        <Tooltip
          formatter={(v) => [v.toFixed(3), 'Contribution']}
          contentStyle={{ borderRadius: 8, border: '1px solid #EBE3D0', fontSize: 12 }}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={14}>
          {data.map((_, i) => (
            <Cell key={i} fill={color} fillOpacity={1 - i * 0.22} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
