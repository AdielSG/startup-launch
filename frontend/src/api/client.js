import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'https://backend-three-beta-98.vercel.app',
  headers: { 'Content-Type': 'application/json' },
})

export default client
