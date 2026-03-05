import { useEffect, useState } from 'react'
import client from '../api/client'

export function useSettings() {
  const [settings, setSettings] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    client.get('/settings/').then((res) => setSettings(res.data))
  }, [])

  async function updateSettings(data) {
    setSaving(true)
    try {
      const res = await client.put('/settings/', data)
      setSettings(res.data)
    } finally {
      setSaving(false)
    }
  }

  return { settings, saving, updateSettings }
}
