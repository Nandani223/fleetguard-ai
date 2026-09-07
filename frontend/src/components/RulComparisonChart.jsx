import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList } from 'recharts'

const COLOR_MAP = { Green: '#16A34A', Amber: '#D97706', Red: '#E5484D' }

/** Two real bars: mileage-only baseline vs. risk-adjusted RUL, in days.
 * Makes the "same VIN, same signals, consistent story" cross-check
 * (baseline compressed by the live failure probability) visible at a
 * glance instead of only readable as two separate numbers. */
export default function RulComparisonChart({ baselineDays, adjustedDays, tier }) {
  const color = COLOR_MAP[tier] || '#E1794B'
  const data = [
    { name: 'Mileage baseline', days: baselineDays, fill: '#F6D9C3' },
    { name: 'Risk-adjusted RUL', days: adjustedDays, fill: color },
  ]

  return (
    <ResponsiveContainer width="100%" height={130}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 40, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#EBE3D0" horizontal={false} />
        <XAxis type="number" tick={{ fill: '#A69C87', fontSize: 11 }} axisLine={{ stroke: '#EBE3D0' }} tickLine={false} />
        <YAxis
          type="category"
          dataKey="name"
          width={120}
          tick={{ fill: '#211E17', fontSize: 12 }}
          axisLine={{ stroke: '#EBE3D0' }}
          tickLine={false}
        />
        <Tooltip
          formatter={(v) => [`${v.toLocaleString()} days`, '']}
          contentStyle={{ borderRadius: 8, border: '1px solid #EBE3D0', fontSize: 12 }}
        />
        <Bar dataKey="days" radius={[0, 4, 4, 0]} maxBarSize={22}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.fill} />
          ))}
          <LabelList dataKey="days" position="right" formatter={(v) => v.toLocaleString()} style={{ fill: '#211E17', fontSize: 12, fontWeight: 600 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
