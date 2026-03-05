import { useEffect, useState } from 'react'
import client from '../api/client'

export function useLaunches(source = null) {
  const [launches, setLaunches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const params = source ? { source } : {}
    client
      .get('/launches/', { params })
      .then((res) => setLaunches(res.data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [source])

  return { launches, loading, error }
}
