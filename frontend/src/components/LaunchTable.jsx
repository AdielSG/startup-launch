import { useState } from 'react'
import {
  formatFunding,
  getLiLikes,
  getTotalFunding,
  getXLikes,
  isPoorPerformer,
} from '../data/mockData'
import DmModal from './DmModal'
import LinkedInModal from './LinkedInModal'
import StatusBadge from './StatusBadge'

const STAGE_STYLES = {
  Early:  'bg-gray-100 text-gray-600',
  Growth: 'bg-blue-50 text-blue-700',
  Public: 'bg-green-50 text-green-700',
}

function StageBadge({ stage }) {
  if (!stage) return null
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${STAGE_STYLES[stage] ?? 'bg-gray-100 text-gray-500'}`}>
      {stage}
    </span>
  )
}

// Small LinkedIn "in" icon used inline in the table cell
function LinkedInIcon() {
  return (
    <svg width={12} height={12} viewBox="0 0 24 24" fill="currentColor" className="shrink-0">
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  )
}

// X / Twitter logo icon
function XIcon() {
  return (
    <svg width={11} height={11} viewBox="0 0 24 24" fill="currentColor" className="shrink-0">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.259 5.63zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  )
}

export default function LaunchTable({ companies, thresholds, onReload }) {
  const [dmTarget, setDmTarget]   = useState(null)
  const [liTarget, setLiTarget]   = useState(null)

  if (!companies.length) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 py-16 text-center text-gray-400 text-sm">
        No companies match the current filters.
      </div>
    )
  }

  return (
    <>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="px-4 py-3 text-left   text-xs font-semibold text-gray-500 uppercase tracking-wide">Company</th>
              <th className="px-4 py-3 text-left   text-xs font-semibold text-gray-500 uppercase tracking-wide">Batch</th>
              <th className="px-4 py-3 text-right  text-xs font-semibold text-gray-500 uppercase tracking-wide">Funding</th>
              <th className="px-4 py-3 text-right  text-xs font-semibold text-gray-500 uppercase tracking-wide">X Likes</th>
              <th className="px-4 py-3 text-right  text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <span className="flex items-center justify-end gap-1">
                  <LinkedInIcon />
                  Likes
                </span>
              </th>
              <th className="px-4 py-3 text-left   text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
              <th className="px-4 py-3 text-left   text-xs font-semibold text-gray-500 uppercase tracking-wide">Contact</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {companies.map(c => {
              const poor    = isPoorPerformer(c, thresholds)
              const xLikes  = getXLikes(c)
              // Prefer the dedicated company column; fall back to launch_posts (mock data)
              const liLikes = c.linkedin_likes ?? getLiLikes(c)
              const contact = c.contacts?.[0]

              return (
                <tr
                  key={c.id}
                  className={poor ? 'bg-red-50' : 'bg-white hover:bg-gray-50 transition-colors'}
                >
                  {/* Company name — red left border for poor performers */}
                  <td className={`px-4 py-3.5 ${poor ? 'border-l-4 border-l-red-400' : 'border-l-4 border-l-transparent'}`}>
                    <div className="flex items-center gap-1.5">
                      <span className="font-medium text-gray-900">{c.name}</span>
                      <StageBadge stage={c.funding_stage} />
                    </div>
                    {c.description && (
                      <div className="text-xs text-gray-400 mt-0.5 max-w-xs truncate">
                        {c.description}
                      </div>
                    )}
                  </td>

                  <td className="px-4 py-3.5">
                    <span className="text-xs font-medium text-gray-600 bg-gray-100 px-2 py-0.5 rounded">
                      {c.yc_batch ?? '—'}
                    </span>
                  </td>

                  <td className="px-4 py-3.5 text-right font-medium text-gray-700 tabular-nums">
                    {formatFunding(getTotalFunding(c))}
                  </td>

                  {/* X Likes */}
                  <td className={`px-4 py-3.5 text-right font-medium tabular-nums ${
                    xLikes !== null && xLikes < thresholds.xLikes ? 'text-red-600' : 'text-gray-700'
                  }`}>
                    {xLikes !== null ? xLikes.toLocaleString() : '—'}
                  </td>

                  {/* LinkedIn Likes — number + icon button to open modal */}
                  <td className="px-4 py-3.5">
                    <div className="flex items-center justify-end gap-1.5">
                      <span className={`font-medium tabular-nums ${
                        liLikes !== null && liLikes < thresholds.liLikes
                          ? 'text-red-600'
                          : 'text-gray-700'
                      }`}>
                        {liLikes !== null
                          ? liLikes.toLocaleString()
                          : <span className="text-gray-300 text-xs italic font-normal">pending</span>
                        }
                      </span>
                      <button
                        onClick={() => setLiTarget(c)}
                        title="Fetch LinkedIn post metrics"
                        className="w-5 h-5 flex items-center justify-center rounded text-[#0A66C2] hover:bg-blue-50 transition-colors"
                      >
                        <LinkedInIcon />
                      </button>
                    </div>
                  </td>

                  <td className="px-4 py-3.5">
                    <StatusBadge poor={poor} />
                  </td>

                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-2">
                      {contact?.linkedin_url && (
                        <a
                          href={contact.linkedin_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          title="View founder on LinkedIn"
                          className="text-[#0A66C2] hover:opacity-70 transition-opacity"
                        >
                          <LinkedInIcon />
                        </a>
                      )}
                      {contact?.x_handle && (
                        <a
                          href={`https://x.com/${contact.x_handle}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          title={`@${contact.x_handle} on X`}
                          className="text-gray-900 hover:opacity-70 transition-opacity"
                        >
                          <XIcon />
                        </a>
                      )}
                      {!contact?.linkedin_url && !contact?.x_handle && (
                        <span className="text-gray-300 text-xs">—</span>
                      )}
                    </div>
                  </td>

                  <td className="px-4 py-3.5 text-right pr-5">
                    {poor && (
                      <button
                        onClick={() => setDmTarget(c)}
                        className="text-xs px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white rounded-lg font-medium transition-colors"
                      >
                        Draft DM
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {dmTarget && (
        <DmModal company={dmTarget} onClose={() => setDmTarget(null)} />
      )}
      {liTarget && (
        <LinkedInModal
          company={liTarget}
          onClose={() => setLiTarget(null)}
          onSuccess={() => {
            setLiTarget(null)
            onReload?.()
          }}
        />
      )}
    </>
  )
}
