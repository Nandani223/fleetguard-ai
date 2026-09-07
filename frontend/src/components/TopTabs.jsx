import { NavLink } from 'react-router-dom'
import { useParts } from '../hooks/usePartContext'

const TABS = [
  { to: '/', label: 'Overview' },
  { to: '/rule-builder', label: 'Rule Builder' },
  { to: '/failure-probability', label: 'Failure Probability', badgeKey: 'redTier' },
  { to: '/rul-explorer', label: 'RUL Explorer' },
  { to: '/maintenance-calendar', label: 'Maintenance Calendar' },
  { to: '/cost-impact', label: 'Cost Impact' },
]

export default function TopTabs() {
  const { redTierVehicles } = useParts()
  const badgeCounts = { redTier: redTierVehicles.length }

  return (
    <div className="flex items-center gap-1 border-b border-line px-6">
      {TABS.map(({ to, label, badgeKey }) => {
        const badgeCount = badgeKey ? badgeCounts[badgeKey] : 0
        return (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-1.5 px-3.5 py-3 text-sm font-medium border-b-2 -mb-px transition-colors ${
                isActive
                  ? 'border-brand text-brand-dim'
                  : 'border-transparent text-ink-dim hover:text-ink'
              }`
            }
          >
            {label}
            {badgeCount > 0 && (
              <span className="inline-flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full bg-risk-red text-white text-[10px] font-bold leading-none">
                {badgeCount > 99 ? '99+' : badgeCount}
              </span>
            )}
          </NavLink>
        )
      })}
    </div>
  )
}
