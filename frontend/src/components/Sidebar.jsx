import { Gauge } from 'lucide-react'

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 bg-surface border-r border-line flex flex-col">
      <div className="px-5 py-5 border-b border-line">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand flex items-center justify-center shadow-pop shrink-0">
            <Gauge size={17} strokeWidth={2.25} className="text-white" />
          </div>
          <div className="min-w-0">
            <div className="font-semibold text-ink text-[15px] leading-tight tracking-tight">FleetGuard AI</div>
            <div className="text-xs text-ink-faint leading-tight">Predictive Maintenance</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4">
        <div className="px-3 py-2 text-xs font-semibold text-ink-faint uppercase tracking-wide">
          Fleet Intelligence
        </div>
        <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-brand-soft text-brand-dim text-sm font-medium">
          <div className="w-1.5 h-1.5 rounded-full bg-brand" />
          Predictive Failure Engine
        </div>
      </nav>

      <div className="px-5 py-4 border-t border-line text-xs text-ink-faint">
        Fleet Ops Console
      </div>
    </aside>
  )
}
