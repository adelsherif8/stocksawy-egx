import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Minus, RefreshCw } from 'lucide-react'

const SECTOR_ICONS = {
  'Banking & Finance':          '🏦',
  'Oil & Gas':                  '🛢️',
  'Real Estate & Construction': '🏗️',
  'Telecom & Technology':       '📡',
  'Food & Beverages':           '🌾',
  'Fertilizers & Chemicals':    '🧪',
  'Steel & Manufacturing':      '⚙️',
  'Tourism & Hospitality':      '✈️',
  'Pharmaceuticals & Healthcare':'💊',
  'Mining & Metals':            '⛏️',
  'Suez Canal & Logistics':     '🚢',
}

function SectorCard({ item }) {
  const isBullish = item.sentiment === 'BULLISH'
  const isBearish = item.sentiment === 'BEARISH'

  const bg    = isBullish ? 'bg-emerald-50 border-emerald-200'  : isBearish ? 'bg-red-50 border-red-200'    : 'bg-gray-50 border-gray-200'
  const text  = isBullish ? 'text-emerald-700'                  : isBearish ? 'text-red-600'                 : 'text-gray-500'
  const bar   = isBullish ? 'bg-emerald-500'                    : isBearish ? 'bg-red-500'                   : 'bg-gray-300'
  const Icon  = isBullish ? TrendingUp                          : isBearish ? TrendingDown                   : Minus

  // Score from -1 to +1 → bar width 0–100%
  const barWidth = Math.round(Math.abs(item.score) * 100)

  return (
    <div className={`rounded-xl border p-3.5 ${bg}`} style={{boxShadow:'0 1px 3px rgba(0,0,0,0.04)'}}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-base">{SECTOR_ICONS[item.sector] || '📊'}</span>
            <span className="text-gray-800 font-semibold text-xs leading-tight">{item.sector}</span>
          </div>
          {item.stocks_affected > 0 && (
            <span className="text-gray-400 text-xs">{item.stocks_affected} stocks · {item.total_signals} signals</span>
          )}
        </div>
        <div className={`flex items-center gap-1 ${text}`}>
          <Icon size={13} />
          <span className="text-xs font-bold">{item.sentiment}</span>
        </div>
      </div>

      {/* Sentiment bar */}
      <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${bar}`} style={{ width: `${barWidth}%` }} />
      </div>

      {item.total_signals > 0 && (
        <div className="flex gap-3 mt-2 text-xs text-gray-400">
          <span className="text-emerald-600 font-medium">▲ {item.bullish}</span>
          <span className="text-red-500 font-medium">▼ {item.bearish}</span>
          <span>— {item.neutral}</span>
        </div>
      )}

      {item.total_signals === 0 && (
        <p className="text-xs text-gray-400 mt-1">No signals today</p>
      )}
    </div>
  )
}

export default function SectorHeatmap() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/heatmap')
      const json = await res.json()
      setData(json.heatmap || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const bullishCount = data.filter(d => d.sentiment === 'BULLISH').length
  const bearishCount = data.filter(d => d.sentiment === 'BEARISH').length

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-gray-800 font-semibold text-sm">Sector Heatmap</h2>
          <p className="text-gray-400 text-xs mt-0.5">Based on today's news sentiment</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-2 text-xs">
            <span className="text-emerald-600 font-bold">{bullishCount} up</span>
            <span className="text-red-500 font-bold">{bearishCount} down</span>
          </div>
          <button onClick={load} className="p-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors">
            <RefreshCw size={12} className={`text-gray-500 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="text-xs text-red-500 bg-red-50 border border-red-200 rounded-lg p-2 mb-3">
          {error} — make sure backend is running
        </div>
      )}

      {/* Grid */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="grid grid-cols-2 gap-2.5">
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="rounded-xl border border-gray-200 bg-gray-50 p-3.5 animate-pulse h-20" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2.5">
            {data.map(item => <SectorCard key={item.sector} item={item} />)}
          </div>
        )}
      </div>
    </div>
  )
}
