const ITEMS = [
  {
    icon: '💰',
    title: 'YC Deal',
    body: "Companies showing 'YC Deal' in the funding column received the standard $500K investment from Y Combinator. This is the same for all YC W25 batch companies.",
  },
  {
    icon: '🎥',
    title: 'Launch Videos',
    body: 'Rows with a 🎥 badge contain a real launch video. Click ▶ Watch to view it directly on X.',
  },
  {
    icon: '⭐',
    title: 'Assessment List',
    body: "Select '★ Assessment List' in the Batch filter to see the 30 curated launch videos from the assessment.",
  },
  {
    icon: '🔴',
    title: 'Poor Performers',
    body: 'Red rows indicate launches that performed below the configured threshold. Use the Draft DM button to generate an outreach message.',
  },
]

export default function WelcomeModal({ onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="bg-indigo-600 px-6 py-5">
          <h2 className="text-white text-lg font-semibold">Welcome to Launch Tracker</h2>
          <p className="text-indigo-200 text-sm mt-0.5">A few things to know before you start</p>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {ITEMS.map(({ icon, title, body }) => (
            <div key={title} className="flex gap-3">
              <span className="text-xl leading-none mt-0.5 shrink-0">{icon}</span>
              <div>
                <p className="text-sm font-semibold text-gray-900">{title}</p>
                <p className="text-sm text-gray-500 mt-0.5">{body}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-6 pb-5">
          <button
            onClick={onClose}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition-colors"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  )
}
