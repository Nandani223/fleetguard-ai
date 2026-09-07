import { createContext, useContext, useEffect, useState } from 'react'
import { listParts } from '../api/client'

const PartContext = createContext(null)

export function PartProvider({ children }) {
  const [parts, setParts] = useState([])
  const [selectedPartCode, setSelectedPartCode] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    listParts()
      .then((data) => {
        setParts(data)
        if (data.length > 0) setSelectedPartCode(data[0].part_code)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const selectedPart = parts.find((p) => p.part_code === selectedPartCode) || null

  return (
    <PartContext.Provider value={{ parts, selectedPart, selectedPartCode, setSelectedPartCode, loading, error }}>
      {children}
    </PartContext.Provider>
  )
}

export function useParts() {
  const ctx = useContext(PartContext)
  if (!ctx) throw new Error('useParts must be used within PartProvider')
  return ctx
}
