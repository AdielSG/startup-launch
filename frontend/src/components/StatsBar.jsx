import {
  formatFunding,
  getLiLikes,
  getTotalFunding,
  getXLikes,
  isPoorPerformer,
  THRESHOLDS,
} from '../data/mockData'

function StatCard({ label, value, sub, accent }) {
  const accentMap = {
    blue:   'bg-blue-50 text-blue-600',
    green:  'bg-emerald-50 text-emerald-600',
    purple: 'bg-violet-50 text-violet-600',
    red:    'bg-red-50 text-red-600',
  }
  const dotMap = {
    blue:   'bg-blue-500',
    green:  'bg-emerald-500',
    purple: 'bg-violet-500',
    red:    'bg-red-500',
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 px-5 py-4 flex items-start gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${accentMap[accent]}`}>
        <span className={`w-2.5 h-2.5 rounded-full ${dotMap[accent]}`} />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900 leading-tight">{value}</p>
        <p className="text-sm text-gray-500 mt-0.5">{label}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

export default function StatsBar({ companies, thresholds = THRESHOLDS }) {
  const total = companies.length

  const avgFunding = companies.length
    ? companies.reduce((s, c) => s + getTotalFunding(c), 0) / companies.length
    : 0

  const xLikesAll = companies.map(getXLikes).filter(v => v !== null)
  const avgX = xLikesAll.length
    ? Math.round(xLikesAll.reduce((s, v) => s + v, 0) / xLikesAll.length)
    : 0

  const liLikesAll = companies.map(getLiLikes).filter(v => v !== null)
  const avgLi = liLikesAll.length
    ? Math.round(liLikesAll.reduce((s, v) => s + v, 0) / liLikesAll.length)
    : 0

  const poorCount = companies.filter(c => isPoorPerformer(c, thresholds)).length

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          label="Companies tracked"
          value={total.toLocaleString()}
          sub="from YC + scrapers"
          accent="blue"
        />
        <StatCard
          label="Avg funding raised"
          value={formatFunding(avgFunding)}
          sub="across all rounds"
          accent="green"
        />
        <StatCard
          label="Avg engagement"
          value={avgX.toLocaleString()}
          sub={`X likes · ${avgLi.toLocaleString()} LinkedIn`}
          accent="purple"
        />
        <StatCard
          label="Poor performers"
          value={poorCount.toLocaleString()}
          sub={`${((poorCount / total) * 100).toFixed(0)}% of total — DM candidates`}
          accent="red"
        />
      </div>
    </div>
  )
}
