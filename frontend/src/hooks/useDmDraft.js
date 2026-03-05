import { useState } from 'react'
import client from '../api/client'

export function useDmDraft() {
  const [draft, setDraft] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function generate(launchId, tone = 'professional') {
    setLoading(true)
    setError(null)
    try {
      const res = await client.post('/dm/draft', { launch_id: launchId, tone })
      setDraft(res.data.dm_text)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  return { draft, loading, error, generate }
}
