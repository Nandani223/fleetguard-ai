import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { signalLabel } from '../constants'

/** Real horizontal bar chart of |point-biserial r| per signal, sorted
 * strongest-first. Bars for excluded (weak, <0.08) signals render muted
 * so the chart visually explains the default include/exclude split. */
export default function CorrelationBarChart({ signals }) {
  const data = [...signals]
    .sort((a, b) => Math.abs(b.point_biserial_r) - Math.abs(a.point_biserial_r))
    .map((s) => ({
      name: signalLabel(s.signal),
      magnitude: Math.round(Math.abs(s.point_biserial_r) * 1000) / 10,
      signed: s.point_biserial_r,
      strong: Math.abs(s.point_biserial_r) > 0.08,
    }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#EBE3D0" horizontal={false} />
        <XAxis
          type="number"
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
          tick={{ fill: '#A69C87', fontSize: 11 }}
          axisLine={{ stroke: '#EBE3D0' }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={140}
          tick={{ fill: '#211E17', fontSize: 12 }}
          axisLine={{ stroke: '#EBE3D0' }}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: '#F2F1FA' }}
          formatter={(value, _name, props) => [`${props.payload.signed > 0 ? '+' : ''}${props.payload.signed.toFixed(3)} r`, 'Correlation']}
          contentStyle={{ borderRadius: 8, border: '1px solid #EBE3D0', fontSize: 12 }}
        />
        <Bar dataKey="magnitude" radius={[0, 4, 4, 0]} maxBarSize={16}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.strong ? '#9cc0fb' : '#c7defb'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
