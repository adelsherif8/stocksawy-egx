import { RefreshCw, TrendingUp, Activity } from 'lucide-react'

export default function Header({ lastUpdated, onRefresh, loading }) {
  const formatTime = (ts) => {
    if (!ts) return '--'
    return new Date(ts * 1000).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50" style={{boxShadow:'0 1px 3px rgba(0,0,0,0.06)'}}>
      <div className="max-w-[1600px] mx-auto px-6 py-3.5 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <img src="/logo.svg" alt="Stocksawy" className="w-10 h-10 rounded-xl" style={{boxShadow:'0 2px 8px rgba(0,0,0,0.18)'}} />
          <div>
            <h1 className="text-gray-900 font-bold text-base leading-none tracking-tight">
              <span>Stock</span><span className="text-amber-500">sawy</span>
            </h1>
            <p className="text-gray-400 text-xs mt-0.5">Egyptian Stock Exchange · AI Analysis</p>
          </div>
        </div>

        {/* Center: live status */}
        <div className="hidden md:flex items-center gap-5">
          <div className="flex items-center gap-2">
            <Activity size={13} className="text-gray-400" />
            <span className="text-gray-400 text-xs">Updated</span>
            <span className="text-gray-700 text-xs font-mono font-semibold">{formatTime(lastUpdated)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 pulse-dot" />
            <span className="text-emerald-600 text-xs font-bold tracking-wide">LIVE</span>
          </div>
        </div>

        {/* Refresh */}
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-900 hover:bg-gray-800 text-white text-xs font-semibold tracking-wide transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          style={{boxShadow:'0 1px 3px rgba(0,0,0,0.15)'}}
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          {loading ? 'FETCHING...' : 'REFRESH'}
        </button>
      </div>
    </header>
  )
}
