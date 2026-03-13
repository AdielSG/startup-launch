import { useState } from 'react'
import { THRESHOLDS, isPoorPerformer } from './data/mockData'
import { useCompanies } from './hooks/useCompanies'
import { useSettings } from './hooks/useSettings'
import { triggerScrape } from './api/companies'
import Sidebar from './components/Sidebar'
import StatsBar from './components/StatsBar'
import FilterBar from './components/FilterBar'
import LaunchTable from './components/LaunchTable'
import SettingsPanel from './components/SettingsPanel'
import WelcomeModal from './components/WelcomeModal'

// ── Inline loading / error states ─────────────────────────────────────────────

function Spinner() {
  return (
    <div className="flex items-center justify-center gap-3 py-24 text-gray-400 text-sm">
      <span className="w-5 h-5 border-2 border-gray-200 border-t-indigo-500 rounded-full animate-spin" />
      Loading companies…
    </div>
  )
}

function ErrorBanner({ message, onRetry }) {
  return (
    <div className="mx-6 mt-6 bg-red-50 border border-red-200 rounded-xl px-5 py-4 flex items-start gap-4">
      <span className="text-red-500 text-lg leading-none mt-0.5">!</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-red-800">Could not load companies</p>
        <p className="text-xs text-red-600 mt-0.5 break-words">{message}</p>
      </div>
      <button
        onClick={onRetry}
        className="text-xs font-medium text-red-700 hover:text-red-900 bg-red-100 hover:bg-red-200 px-3 py-1.5 rounded-lg transition-colors shrink-0"
      >
        Retry
      </button>
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const { companies, loading, error, reload } = useCompanies()

  const { settings, updateSettings } = useSettings()

  const [welcomeOpen,  setWelcomeOpen]  = useState(() => !localStorage.getItem('welcomeSeen'))
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [scraping,     setScraping]     = useState(false)
  const [scrapeToast,  setScrapeToast]  = useState(null)   // { type: 'ok'|'error', msg: string }
  const [activeNav,    setActiveNav]    = useState('dashboard')
  const [batchFilter,  setBatchFilter]  = useState('')
  const [perfFilter,   setPerfFilter]   = useState('')

  // Derive thresholds from backend settings; fall back to defaults while loading
  const thresholds = settings
    ? { xLikes: settings.twitter_likes_threshold, liLikes: settings.linkedin_likes_threshold }
    : THRESHOLDS

  async function handleSaveSettings(newThresholds) {
    await updateSettings({
      twitter_likes_threshold:  newThresholds.xLikes,
      linkedin_likes_threshold: newThresholds.liLikes,
    })
  }

  async function handleRefresh() {
    setScraping(true)
    setScrapeToast(null)
    try {
      // Block until the full YC + Twitter pipeline finishes (up to 5 min)
      const result = await triggerScrape()
      await reload()
      setScrapeToast({
        type: result.status === 'ok' ? 'ok' : 'error',
        msg:  result.status === 'ok'
          ? `Scraped ${result.companies} companies, found ${result.tweets} tweets`
          : `Scrape error: ${result.detail ?? 'unknown'}`,
      })
    } catch (err) {
      console.error('Scrape trigger failed:', err)
      await reload()
      setScrapeToast({ type: 'error', msg: 'Scrape request failed — check the backend logs' })
    } finally {
      setScraping(false)
      // Auto-dismiss toast after 6 seconds
      setTimeout(() => setScrapeToast(null), 6000)
    }
  }

  // Apply client-side filters on top of the live data
  const filtered = companies
    .filter(c => !batchFilter || c.yc_batch === batchFilter)
    .filter(c => {
      if (!perfFilter) return true
      const poor = isPoorPerformer(c, thresholds)
      return perfFilter === 'poor' ? poor : !poor
    })

  // Show initial spinner only when we have no data yet
  const showSpinner = loading && companies.length === 0

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        activeNav={activeNav}
        onNav={setActiveNav}
        onOpenSettings={() => setSettingsOpen(true)}
        onRefresh={handleRefresh}
        scraping={scraping}
      />

      <div className="flex-1 flex flex-col overflow-hidden bg-gray-50">
        {/* Stats bar always shows (uses whatever data is loaded) */}
        <StatsBar companies={filtered} thresholds={thresholds} />

        {/* Scrape result toast */}
        {scrapeToast && (
          <div className={`mx-6 mt-4 px-4 py-3 rounded-lg text-sm font-medium flex items-center justify-between ${
            scrapeToast.type === 'ok'
              ? 'bg-green-50 border border-green-200 text-green-800'
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}>
            <span>{scrapeToast.type === 'ok' ? '✓' : '!'} {scrapeToast.msg}</span>
            <button onClick={() => setScrapeToast(null)} className="ml-4 opacity-50 hover:opacity-100 text-lg leading-none">×</button>
          </div>
        )}

        <main className="flex-1 overflow-auto">
          {showSpinner ? (
            <Spinner />
          ) : error ? (
            <ErrorBanner message={error} onRetry={reload} />
          ) : (
            <div className="px-6 py-5 space-y-4">
              {/* Scraping-in-progress banner */}
              {scraping && (
                <div className="flex items-center gap-2 text-xs text-indigo-600 bg-indigo-50 border border-indigo-200 rounded-lg px-3 py-2">
                  <span className="w-3 h-3 border-2 border-indigo-200 border-t-indigo-500 rounded-full animate-spin shrink-0" />
                  Scraping YC W25 companies and searching for tweets — this may take a few minutes…
                </div>
              )}
              {/* Stale-data banner while re-fetching (after scrape) */}
              {loading && !scraping && (
                <div className="flex items-center gap-2 text-xs text-indigo-600">
                  <span className="w-3 h-3 border-2 border-indigo-200 border-t-indigo-500 rounded-full animate-spin" />
                  Refreshing…
                </div>
              )}
              <FilterBar
                batch={batchFilter}
                onBatchChange={setBatchFilter}
                perf={perfFilter}
                onPerfChange={setPerfFilter}
              />
              <LaunchTable companies={filtered} thresholds={thresholds} onReload={reload} />
            </div>
          )}
        </main>
      </div>

      {settingsOpen && (
        <SettingsPanel
          thresholds={thresholds}
          onSave={handleSaveSettings}
          onClose={() => setSettingsOpen(false)}
        />
      )}

      {welcomeOpen && (
        <WelcomeModal onClose={() => {
          localStorage.setItem('welcomeSeen', '1')
          setWelcomeOpen(false)
        }} />
      )}
    </div>
  )
}
