import { useState } from 'react'
import { submitLinkedinUrl } from '../api/companies'

// ── Small LinkedIn brand icon ──────────────────────────────────────────────────
function LinkedInIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  )
}

export default function LinkedInModal({ company, onClose, onSuccess }) {
  const [url,     setUrl]     = useState(company.linkedin_post_url ?? '')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [result,  setResult]  = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!url.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await submitLinkedinUrl(company.id, url.trim())
      setResult(data)
      onSuccess()           // trigger a reload in the parent
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.message ||
        'Failed to fetch LinkedIn metrics. Check the URL and try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl border border-gray-200 shadow-xl w-full max-w-md">

        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <span className="text-[#0A66C2]">
              <LinkedInIcon size={18} />
            </span>
            <div>
              <h2 className="text-base font-semibold text-gray-900">Fetch LinkedIn Metrics</h2>
              <p className="text-xs text-gray-400 mt-0.5">{company.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors leading-none mt-0.5"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">

          {/* ⚠️ Latency warning — always visible */}
          <div className="flex gap-2.5 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
            <span className="text-amber-500 text-base leading-none mt-0.5 shrink-0">⏱</span>
            <p className="text-xs text-amber-800 leading-relaxed">
              <strong>This can take up to 60 seconds.</strong> Apify needs to scrape the LinkedIn
              post in real time. The spinner will keep running — please don't close this window
              until the results appear.
            </p>
          </div>

          {/* URL form */}
          {!result && (
            <form onSubmit={handleSubmit} className="space-y-3">
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-gray-700">LinkedIn post URL</span>
                <input
                  type="url"
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  placeholder="https://www.linkedin.com/posts/..."
                  required
                  disabled={loading}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-[#0A66C2] focus:border-[#0A66C2] disabled:bg-gray-50 disabled:text-gray-400"
                />
              </label>

              {error && (
                <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading || !url.trim()}
                className="w-full py-2.5 bg-[#0A66C2] hover:bg-[#004182] text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Fetching via Apify… (up to 60 s)
                  </>
                ) : (
                  <>
                    <LinkedInIcon size={14} />
                    {url && company.linkedin_post_url ? 'Re-fetch Metrics' : 'Fetch Metrics'}
                  </>
                )}
              </button>
            </form>
          )}

          {/* Success result */}
          {result && (
            <div className="space-y-3">
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 flex items-center gap-2">
                <span className="text-emerald-500 text-base">✓</span>
                <span className="text-sm font-medium text-emerald-800">Metrics fetched successfully</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-50 rounded-xl px-4 py-3 text-center">
                  <p className="text-2xl font-bold text-gray-900">{result.linkedin_likes.toLocaleString()}</p>
                  <p className="text-xs text-gray-500 mt-0.5">Likes</p>
                </div>
                <div className="bg-gray-50 rounded-xl px-4 py-3 text-center">
                  <p className="text-2xl font-bold text-gray-900">{result.linkedin_reposts.toLocaleString()}</p>
                  <p className="text-xs text-gray-500 mt-0.5">Reposts</p>
                </div>
              </div>

              <p className="text-xs text-gray-400 text-center">
                Fetched {new Date(result.linkedin_fetched_at).toLocaleString()}
              </p>

              <button
                onClick={onClose}
                className="w-full py-2 bg-gray-900 hover:bg-gray-700 text-white rounded-xl text-sm font-medium transition-colors"
              >
                Done
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
