import { createContext, useContext, useEffect, useState, useRef } from 'react'
import { useMsal } from '@azure/msal-react'
import { loginRequest } from '../msalConfig'
import { ssoLogin, passwordLogin, setAuthToken } from '../api/client'

const AuthContext = createContext(null)
const STORAGE_KEY = 'fleetguard_session'

export function AuthProvider({ children }) {
  const { instance } = useMsal()
  const [user, setUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [error, setError] = useState(null)
  const [msLoading, setMsLoading] = useState(false)
  const handledRedirect = useRef(false)

  useEffect(() => {
    async function init() {
      // 1) Are we landing back here right after a Microsoft redirect?
      //    (loginRedirect sends the whole page to Microsoft, then back —
      //    no popup, so nothing to conflict with block_nested_popups.)
      if (!handledRedirect.current) {
        handledRedirect.current = true
        try {
          const result = await instance.handleRedirectPromise()
          if (result?.idToken) {
            const res = await ssoLogin(result.idToken)
            setAuthToken(res.access_token)
            setUser(res.user)
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ token: res.access_token, user: res.user }))
            setAuthLoading(false)
            return
          }
        } catch (err) {
          setError(err.message || 'Microsoft sign-in failed')
        }
      }

      // 2) Otherwise, restore a normal session from a previous login (any method)
      const cached = sessionStorage.getItem(STORAGE_KEY)
      if (cached) {
        const { token, user } = JSON.parse(cached)
        setAuthToken(token)
        setUser(user)
      }
      setAuthLoading(false)
    }
    init()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function login(email, password) {
    setError(null)
    try {
      const res = await passwordLogin(email, password)
      setAuthToken(res.access_token)
      setUser(res.user)
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ token: res.access_token, user: res.user }))
    } catch (err) {
      setError(err.message || 'Sign-in failed')
      throw err
    }
  }

  function loginWithMicrosoft() {
    setMsLoading(true)
    setError(null)
    // Full-page redirect to Microsoft's login screen — the page navigates
    // away entirely and comes back to this same app, where the useEffect
    // above picks up the response via handleRedirectPromise(). No popup
    // window involved, so there's nothing for block_nested_popups to fire on.
    instance.loginRedirect(loginRequest)
  }

  function logout() {
    setAuthToken(null)
    setUser(null)
    sessionStorage.removeItem(STORAGE_KEY)
    instance.clearCache?.()
  }

  const isAdmin = user?.role === 'admin'

  return (
    <AuthContext.Provider value={{ user, authLoading, msLoading, error, isAdmin, login, loginWithMicrosoft, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
