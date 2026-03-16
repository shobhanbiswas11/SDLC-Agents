import { useState, useEffect, useCallback } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

export function useHistory() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  // Fetch history from backend on mount and periodically
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch(`${API_URL}/history`)
        if (response.ok) {
          const data = await response.json()
          setHistory(data || [])
        }
      } catch (err) {
        console.error('Failed to fetch history:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchHistory()
  }, [])

  const addRun = useCallback((run, messages = []) => {
    // Update local state immediately for UI responsiveness
    setHistory(prev => [
      { ...run, messages },
      ...prev.slice(0, 49)
    ])
  }, [])

  const clearHistory = useCallback(async () => {
    try {
      await fetch(`${API_URL}/history`, { method: 'DELETE' })
      setHistory([])
    } catch (err) {
      console.error('Failed to clear history:', err)
    }
  }, [])

  const removeRun = useCallback((id) => {
    // Update local state immediately
    setHistory(prev => prev.filter(r => r.id !== id))
    // Also delete from backend
    fetch(`${API_URL}/history/${id}`, { method: 'DELETE' }).catch(err =>
      console.error('Failed to delete run:', err)
    )
  }, [])

  return { history, addRun, clearHistory, removeRun, loading }
}