import { NavLink } from 'react-router-dom'

const TABS = [
  { to: '/', label: 'Overview' },
  { to: '/rule-builder', label: 'Rule Builder' },
  { to: '/failure-probability', label: 'Failure Probability' },
  { to: '/rul-explorer', label: 'RUL Explorer' },
]

export default function TopTabs() {
  return (
    <div className="flex items-center gap-1 border-b border-line px-6">
      {TABS.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `px-3.5 py-3 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-brand text-brand-dim'
                : 'border-transparent text-ink-dim hover:text-ink'
            }`
          }
        >
          {label}
        </NavLink>
      ))}
    </div>
  )
}
