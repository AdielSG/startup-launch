import { useState } from 'react'

export default function SettingsPanel({ thresholds, onSave, onClose }) {
  const [xLikes,  setXLikes]  = useState(thresholds.xLikes)
  const [liLikes, setLiLikes] = useState(thresholds.liLikes)

  async function handleSave() {
    await onSave({ xLikes: Number(xLikes), liLikes: Number(liLikes) })
    onClose()
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl border border-gray-200 shadow-xl w-full max-w-sm">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Performance Thresholds</h2>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors leading-none"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">
          <p className="text-sm text-gray-500">
            Companies where <strong className="text-gray-700">both</strong> X likes and LinkedIn
            likes fall below these values are flagged as poor performers and show a Draft DM button.
          </p>

          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-gray-700">X / Twitter likes threshold</span>
            <input
              type="number"
              min={0}
              value={xLikes}
              onChange={e => setXLikes(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </label>

          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-gray-700">LinkedIn likes threshold</span>
            <input
              type="number"
              min={0}
              value={liLikes}
              onChange={e => setLiLikes(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </label>
        </div>

        {/* Footer */}
        <div className="flex gap-3 justify-end px-6 pb-5">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium transition-colors"
          >
            Save
          </button>
        </div>

      </div>
    </div>
  )
}
