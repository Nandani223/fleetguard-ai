import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { listParts, listPredictions } from '../api/client'

const PartContext = createContext(null)

export function PartProvider({ children }) {
  const [parts, setParts] = useState([])
  const [selectedPartCode, setSelectedPartCode] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Red-tier alerts + last-scored date for the CURRENTLY SELECTED part.
  // Shared here (rather than fetched separately in TopBar/TopTabs) so the
  // bell, the tab badge, and the "last scored" pill can never disagree —
  // one fetch, three readers.
  const [redTierVehicles, setRedTierVehicles] = useState([])
  const [alertsLoading, setAlertsLoading] = useState(false)
  const [lastScoredDate, setLastScoredDate] = useState(null)

  useEffect(() => {
    listParts()
      .then((data) => {
        setParts(data)
        if (data.length > 0) setSelectedPartCode(data[0].part_code)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const refreshAlerts = useCallback(() => {
    if (!selectedPartCode) return
    setAlertsLoading(true)
    listPredictions(selectedPartCode, undefined, 500)
      .then((data) => {
        setRedTierVehicles(data.filter((p) => p.risk_tier === 'Red'))
        setLastScoredDate(data.length > 0 ? data[0].computed_date : null)
      })
      .catch(() => {
        setRedTierVehicles([])
        setLastScoredDate(null)
      })
      .finally(() => setAlertsLoading(false))
  }, [selectedPartCode])

  useEffect(() => {
    refreshAlerts()
  }, [refreshAlerts])

  const selectedPart = parts.find((p) => p.part_code === selectedPartCode) || null

  return (
    <PartContext.Provider
      value={{
        parts,
        selectedPart,
        selectedPartCode,
        setSelectedPartCode,
        loading,
        error,
        redTierVehicles,
        alertsLoading,
        lastScoredDate,
        refreshAlerts,
      }}
    >
      {children}
    </PartContext.Provider>
  )
}

export function useParts() {
  const ctx = useContext(PartContext)
  if (!ctx) throw new Error('useParts must be used within PartProvider')
  return ctx
}
