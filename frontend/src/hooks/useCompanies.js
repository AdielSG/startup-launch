import { useCallback, useEffect, useState } from 'react'
import { fetchCompanies } from '../api/companies'

/**
 * Fetches all companies from the API.
 * Returns { companies, loading, error, reload }.
 *
 * - loading is true on the initial fetch AND on manual reloads.
 * - error is the human-readable error string, or null.
 * - reload() re-fetches without clearing existing data (stale-while-reload UX).
 */
export function useCompanies() {
  const [companies, setCompanies] = useState([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchCompanies()
      setCompanies(data)
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'Failed to load companies'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return { companies, loading, error, reload: load }
}
