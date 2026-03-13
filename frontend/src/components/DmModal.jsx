import { useState } from 'react'
import {
  formatFunding,
  getLiLikes,
  getTotalFunding,
  getXLikes,
} from '../data/mockData'
import { draftDm } from '../api/companies'

function Chip({ label, value }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">{label}</span>
      <span className="text-sm font-semibold text-gray-800 mt-0.5">{value}</span>
    </div>
  )
}

export default function DmModal({ company, onClose }) {
  const [draft,   setDraft]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [copied,  setCopied]  = useState(false)

  const xLikes  = getXLikes(company)
  const liLikes = getLiLikes(company)

  async function handleGenerate() {
    setLoading(true)
    setDraft(null)
    setError(null)
    try {
      const result = await draftDm(company.id)
      setDraft(result.dm_text)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.message ||
        'Failed to generate DM. Check that OPENAI_API_KEY is set.'
      )
    } finally {
      setLoading(false)
    }
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(draft)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl border border-gray-200 shadow-xl w-full max-w-xl">

        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Draft Outreach DM</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              {company.name} · poor launch performance detected
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors leading-none mt-0.5"
          >
            ✕
          </button>
        </div>

        {/* Stats strip */}
        <div className="px-6 py-3 bg-gray-50 border-b border-gray-100 flex gap-8">
          <Chip label="X Likes"  value={xLikes  !== null ? xLikes.toLocaleString()  : '—'} />
          <Chip label="LinkedIn" value={liLikes !== null ? liLikes.toLocaleString() : '—'} />
          <Chip label="Funding"  value={formatFunding(getTotalFunding(company))} />
          <Chip label="YC Batch" value={company.yc_batch ?? '—'} />
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {!draft && !loading && (
            <>
              {error && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                  {error}
                </p>
              )}
              <button
                onClick={handleGenerate}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition-colors"
              >
                {error ? 'Retry' : 'Generate DM with AI'}
              </button>
            </>
          )}

          {loading && (
            <div className="flex items-center justify-center gap-3 py-8 text-gray-400 text-sm">
              <span className="w-4 h-4 border-2 border-gray-200 border-t-indigo-500 rounded-full animate-spin" />
              Generating personalised outreach…
            </div>
          )}

          {draft && !loading && (
            <>
              <textarea
                readOnly
                value={draft}
                rows={10}
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-700 resize-none leading-relaxed focus:outline-none"
              />
              <div className="flex items-center justify-between">
                <button
                  onClick={handleGenerate}
                  className="text-sm text-gray-400 hover:text-gray-700 transition-colors"
                >
                  Regenerate
                </button>
                <button
                  onClick={handleCopy}
                  className={`px-5 py-2 text-sm rounded-xl font-medium transition-colors ${
                    copied
                      ? 'bg-emerald-500 text-white'
                      : 'bg-gray-900 hover:bg-gray-700 text-white'
                  }`}
                >
                  {copied ? 'Copied!' : 'Copy to Clipboard'}
                </button>
              </div>
            </>
          )}
        </div>

      </div>
    </div>
  )
}
