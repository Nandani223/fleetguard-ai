import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { AlertTriangle, Loader2, LogOut } from 'lucide-react'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import TopTabs from './components/TopTabs'
import ChatPanel from './components/ChatPanel'
import ErrorBoundary from './components/ErrorBoundary'
import Login from './pages/Login'
import { PartProvider, useParts } from './hooks/usePartContext'
import { AuthProvider, useAuth } from './context/AuthContext'
import OverviewPage from './pages/OverviewPage'
import RuleBuilderPage from './pages/RuleBuilderPage'
import FailureProbabilityPage from './pages/FailureProbabilityPage'
import RULExplorerPage from './pages/RULExplorerPage'
import MaintenanceCalendarPage from './pages/MaintenanceCalendarPage'
import CostImpactPage from './pages/CostImpactPage'

const TITLES = {
  '/': 'Overview',
  '/rule-builder': 'Rule Builder',
  '/failure-probability': 'Failure Probability',
  '/rul-explorer': 'RUL Explorer',
  '/maintenance-calendar': 'Maintenance Calendar',
  '/cost-impact': 'Cost Impact',
}

function UserChip() {
  const { user, logout, isAdmin } = useAuth()
  if (!user) return null
  return (
    <div className="flex items-center gap-3 px-5 py-3 border-t border-line">
      <div className="w-8 h-8 rounded-full bg-brand-soft flex items-center justify-center text-brand-dim text-xs font-bold shrink-0">
        {(user.name || user.email)[0].toUpperCase()}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-ink truncate">{user.name || user.email}</p>
        <p className="text-[11px] text-ink-faint truncate">
          {isAdmin ? 'Admin — all fleets' : user.fleet_owner_name || 'Fleet Owner'}
        </p>
      </div>
      <button onClick={logout} className="text-ink-faint hover:text-risk-red transition-colors shrink-0" aria-label="Log out">
        <LogOut size={15} />
      </button>
    </div>
  )
}

function Shell() {
  const location = useLocation()
  const title = TITLES[location.pathname] || 'FleetGuard AI'
  const { loading: partsLoading, error: partsError, parts } = useParts()
  const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg">
      <div className="flex flex-col">
        <Sidebar />
        <UserChip />
      </div>
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar title={title} />
        <TopTabs />
        <main className="flex-1 overflow-y-auto p-6">
          {partsLoading && (
            <div className="flex flex-col items-center justify-center h-full text-center gap-3">
              <Loader2 size={22} className="text-brand animate-spin" />
              <p className="text-sm text-ink-dim">Connecting to FleetGuard backend…</p>
            </div>
          )}

          {!partsLoading && partsError && (
            <div className="flex flex-col items-center justify-center h-full text-center px-6">
              <div className="w-12 h-12 rounded-xl bg-risk-red-soft flex items-center justify-center mb-4">
                <AlertTriangle size={22} className="text-risk-red" />
              </div>
              <p className="font-semibold text-ink mb-1">Can't reach the backend</p>
              <p className="text-sm text-ink-dim max-w-md mb-3">{partsError}</p>
              <div className="text-xs text-ink-dim bg-surface border border-line rounded-lg p-4 max-w-md text-left space-y-1.5 shadow-card">
                <p>Trying to reach: <span className="font-semibold text-ink">{apiBase}</span></p>
                <p className="font-medium text-ink pt-1">Checklist:</p>
                <ul className="list-disc list-inside space-y-0.5">
                  <li>Is <span className="font-mono text-[11px] bg-surface-sunken px-1 py-0.5 rounded">uvicorn app.main:app --reload</span> running?</li>
                  <li>Does .env's VITE_API_BASE_URL match its address?</li>
                  <li>Restart this dev server after changing .env</li>
                </ul>
              </div>
            </div>
          )}

          {!partsLoading && !partsError && parts.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center px-6">
              <div className="w-12 h-12 rounded-xl bg-risk-amber-soft flex items-center justify-center mb-4">
                <AlertTriangle size={22} className="text-risk-amber" />
              </div>
              <p className="font-semibold text-ink mb-1">Backend connected, but no parts found</p>
              <p className="text-sm text-ink-dim max-w-md">
                Run <span className="font-mono text-[11px] bg-surface-sunken px-1 py-0.5 rounded">python scripts/generate_data.py</span> in
                the backend folder to populate the database, then refresh this page.
              </p>
            </div>
          )}

          {!partsLoading && !partsError && parts.length > 0 && (
            <ErrorBoundary key={location.pathname}>
              <Routes>
                <Route path="/" element={<OverviewPage />} />
                <Route path="/rule-builder" element={<RuleBuilderPage />} />
                <Route path="/failure-probability" element={<FailureProbabilityPage />} />
                <Route path="/rul-explorer" element={<RULExplorerPage />} />
                <Route path="/maintenance-calendar" element={<MaintenanceCalendarPage />} />
                <Route path="/cost-impact" element={<CostImpactPage />} />
              </Routes>
            </ErrorBoundary>
          )}
        </main>
      </div>
      <ChatPanel />
    </div>
  )
}

function Gate() {
  const { user, authLoading } = useAuth()

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg">
        <Loader2 size={22} className="text-brand animate-spin" />
      </div>
    )
  }
  if (!user) return <Login />

  return (
    <PartProvider>
      <Shell />
    </PartProvider>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Gate />
      </AuthProvider>
    </BrowserRouter>
  )
}
