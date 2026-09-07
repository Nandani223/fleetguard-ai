import { useState } from 'react'
import { Gauge, ShieldCheck } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

function MicrosoftLogo() {
  return (
    <svg width="16" height="16" viewBox="0 0 21 21" aria-hidden="true">
      <rect x="1" y="1" width="9" height="9" fill="#f25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
      <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
      <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
    </svg>
  )
}

export default function Login() {
  const { login, loginWithMicrosoft, msLoading, error } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await login(email, password)
    } catch {
      // error already surfaced via context
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-11 h-11 rounded-lg bg-brand flex items-center justify-center mb-4 shadow-pop">
            <Gauge size={20} className="text-white" />
          </div>
          <h1 className="font-semibold text-xl text-ink tracking-tight">FleetGuard AI</h1>
          <p className="text-xs uppercase tracking-[0.14em] text-ink-faint mt-1">Predictive Maintenance</p>
        </div>

        <div className="bg-surface border border-line rounded-xl shadow-card px-6 py-7">
          <h2 className="text-sm font-semibold text-ink mb-1">Sign in</h2>
          <p className="text-xs text-ink-dim mb-5">Enter the email and password issued for the demo.</p>

          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-ink-dim mb-1">Email</label>
              <input
                type="email" required autoFocus value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="owner1@fleetguard-demo.com"
                className="w-full bg-surface-sunken border border-line rounded-lg px-3 py-2.5 text-sm text-ink focus:outline-none focus:border-brand"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-ink-dim mb-1">Password</label>
              <input
                type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-surface-sunken border border-line rounded-lg px-3 py-2.5 text-sm text-ink focus:outline-none focus:border-brand"
              />
            </div>

            {error && <p className="text-xs text-risk-red bg-risk-red-soft rounded-md px-3 py-2">{error}</p>}

            <button
              type="submit" disabled={loading || msLoading}
              className="w-full bg-brand text-white rounded-lg py-2.5 text-sm font-semibold hover:brightness-110 transition-all disabled:opacity-50"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="flex items-center gap-3 my-5">
            <div className="h-px flex-1 bg-line" />
            <span className="text-[11px] uppercase tracking-wide text-ink-faint">or</span>
            <div className="h-px flex-1 bg-line" />
          </div>

          <button
            type="button" onClick={loginWithMicrosoft} disabled={loading || msLoading}
            className="w-full flex items-center justify-center gap-2.5 border border-line rounded-lg py-2.5 text-sm font-medium text-ink bg-surface hover:bg-surface-sunken transition-colors disabled:opacity-50"
          >
            <MicrosoftLogo />
            {msLoading ? 'Signing in…' : 'Sign in with Microsoft'}
          </button>
        </div>

        <p className="flex items-center justify-center gap-1.5 text-xs text-ink-faint mt-5">
          <ShieldCheck size={13} />
          Admins see the full fleet; fleet owners see only their own vehicles.
        </p>
      </div>
    </div>
  )
}
