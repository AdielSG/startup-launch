import StatusBadge from './StatusBadge'

export default function LaunchCard({ launch, settings }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold">{launch.company_name}</h3>
        <StatusBadge
          twitterLikes={launch.twitter_likes}
          linkedinLikes={launch.linkedin_likes}
          settings={settings}
        />
      </div>
      {launch.description && (
        <p className="text-sm text-gray-400">{launch.description}</p>
      )}
      <div className="flex gap-4 text-xs text-gray-500 pt-1">
        <span>X: {launch.twitter_likes ?? '—'}</span>
        <span>LI: {launch.linkedin_likes ?? 'pending'}</span>
        <span>
          Funding:{' '}
          {launch.funding_total
            ? `$${(launch.funding_total / 1e6).toFixed(1)}M`
            : '—'}
        </span>
      </div>
    </div>
  )
}
