import { useState } from 'react'
import { TrendingUp, TrendingDown, Minus, Zap, BarChart2, ExternalLink } from 'lucide-react'

const ACTION_CONFIG = {
  BUY:   { color: 'text-emerald-700', lightColor: 'text-emerald-600', bg: 'bg-emerald-50',  border: 'border-emerald-200', pill: 'bg-emerald-600 text-white', icon: TrendingUp },
  SELL:  { color: 'text-red-600',     lightColor: 'text-red-500',     bg: 'bg-red-50',      border: 'border-red-200',     pill: 'bg-red-500 text-white',     icon: TrendingDown },
  WATCH: { color: 'text-orange-600',  lightColor: 'text-orange-500',  bg: 'bg-orange-50',   border: 'border-orange-200',  pill: 'bg-orange-500 text-white',  icon: Minus },
}

const CONF_WEIGHT = { HIGH: 3, MEDIUM: 2, LOW: 1 }

function ConfidenceDots({ level, dotClass }) {
  const count = CONF_WEIGHT[level] || 1
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3].map(i => (
        <span key={i} className={`w-1.5 h-1.5 rounded-full ${i <= count ? dotClass : 'bg-gray-200'}`} />
      ))}
    </div>
  )
}

const DOT_CLASS = {
  BUY: 'bg-emerald-500', SELL: 'bg-red-500', WATCH: 'bg-orange-500'
}

function PriceBadge({ priceData }) {
  if (!priceData?.available) return null
  const isPos = priceData.change_pct >= 0
  return (
    <div className="flex items-center gap-1.5 bg-gray-50 border border-gray-200 rounded-lg px-2 py-1">
      <span className="text-gray-700 text-xs font-mono font-semibold">EGP {priceData.price}</span>
      <span className={`text-xs font-mono font-bold ${isPos ? 'text-emerald-600' : 'text-red-500'}`}>
        {isPos ? '+' : ''}{priceData.change_pct}%
      </span>
    </div>
  )
}

function StockCard({ stock, rank }) {
  const cfg = ACTION_CONFIG[stock.action] || ACTION_CONFIG.WATCH
  const Icon = cfg.icon
  const isPos = stock.expected_change?.startsWith('+')
  const isNeg = stock.expected_change?.startsWith('-')

  return (
    <div className="slide-in rounded-xl bg-white border border-gray-200 hover:-translate-y-0.5 transition-transform cursor-default"
      style={{boxShadow:'0 1px 3px rgba(0,0,0,0.05)'}}>
      <div className="p-3.5">
        <div className="flex items-start gap-3">

          {/* Action icon box */}
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 border ${cfg.bg} ${cfg.border}`}>
            <Icon size={15} className={cfg.color} />
          </div>

          <div className="flex-1 min-w-0">
            {/* Row 1: rank, ticker, action pill */}
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className="text-gray-300 text-xs font-mono">#{rank}</span>
              <a
                href={`https://www.tradingview.com/symbols/EGX-${stock.ticker}/`}
                target="_blank"
                rel="noopener noreferrer"
                className={`font-mono font-bold text-sm hover:underline flex items-center gap-0.5 ${cfg.color}`}
              >
                {stock.ticker}
                <ExternalLink size={10} className="opacity-50" />
              </a>
              <span className={`text-xs font-bold px-2 py-0.5 rounded-md ${cfg.pill}`}>
                {stock.action}
              </span>
              {stock.urgency === 'HIGH' && (
                <span className="flex items-center gap-0.5 text-xs text-red-600 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded-md font-bold">
                  <Zap size={9} />HOT
                </span>
              )}
            </div>

            <p className="text-gray-800 text-xs font-semibold truncate leading-tight">{stock.name}</p>
            <p className="text-gray-400 text-xs mb-1.5">{stock.sector}</p>
            <p className="text-gray-500 text-xs leading-relaxed">{stock.reason}</p>

            {/* Footer stats */}
            <div className="mt-2 pt-2 border-t border-gray-100 space-y-1.5">
              {/* Live price row */}
              {stock.price_data?.available && (
                <PriceBadge priceData={stock.price_data} />
              )}
              <div className="flex items-center gap-3">
                {stock.expected_change && (
                  <span className={`font-mono text-xs font-bold ${isPos ? 'text-emerald-600' : isNeg ? 'text-red-500' : 'text-gray-500'}`}>
                    AI est. {stock.expected_change}
                  </span>
                )}
                <div className="flex items-center gap-1.5">
                  <ConfidenceDots level={stock.confidence} dotClass={DOT_CLASS[stock.action] || 'bg-gray-400'} />
                  <span className="text-xs text-gray-400">{stock.confidence}</span>
                </div>
                {stock.news_count > 1 && (
                  <div className="flex items-center gap-1 text-gray-400 text-xs">
                    <BarChart2 size={10} />
                    {stock.news_count} signals
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const ACTION_FILTERS = ['All', 'BUY', 'SELL', 'WATCH']
const CONF_FILTERS   = ['Any', 'HIGH', 'MEDIUM']

export default function StockRecommendations({ recommendations, loading }) {
  const [actionFilter, setActionFilter] = useState('All')
  const [confFilter,   setConfFilter]   = useState('Any')

  const buyCount   = recommendations.filter(r => r.action === 'BUY').length
  const sellCount  = recommendations.filter(r => r.action === 'SELL').length
  const watchCount = recommendations.filter(r => r.action === 'WATCH').length

  const visible = recommendations.filter(r => {
    if (actionFilter !== 'All' && r.action !== actionFilter) return false
    if (confFilter   !== 'Any' && r.confidence !== confFilter) return false
    return true
  })

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-2">
            <TrendingUp size={14} className="text-gray-500" />
            <span className="text-gray-700 font-semibold text-sm tracking-tight">Stock Signals</span>
          </div>
          <span className="text-gray-400 text-xs">{visible.length}/{recommendations.length}</span>
        </div>

        {/* Summary pills */}
        <div className="flex gap-1.5 mb-3">
          <span className="text-xs px-2.5 py-1 rounded-md bg-emerald-600 text-white font-bold">{buyCount} BUY</span>
          <span className="text-xs px-2.5 py-1 rounded-md bg-red-500 text-white font-bold">{sellCount} SELL</span>
          <span className="text-xs px-2.5 py-1 rounded-md bg-orange-500 text-white font-bold">{watchCount} WATCH</span>
        </div>

        {/* Action filter */}
        <div className="flex gap-1 mb-1.5">
          {ACTION_FILTERS.map(f => (
            <button key={f} onClick={() => setActionFilter(f)}
              className={`text-xs px-2.5 py-1 rounded-md font-semibold transition-all ${
                actionFilter === f ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}>
              {f}
            </button>
          ))}
        </div>

        {/* Confidence filter */}
        <div className="flex gap-1 items-center">
          <span className="text-gray-400 text-xs mr-0.5">Conf:</span>
          {CONF_FILTERS.map(f => (
            <button key={f} onClick={() => setConfFilter(f)}
              className={`text-xs px-2.5 py-1 rounded-md font-semibold transition-all ${
                confFilter === f ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-0.5">
        {loading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-gray-200 bg-white p-3.5 animate-pulse">
              <div className="flex gap-3">
                <div className="w-9 h-9 rounded-lg bg-gray-100" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 bg-gray-100 rounded w-1/3" />
                  <div className="h-3 bg-gray-100 rounded w-2/3" />
                  <div className="h-3 bg-gray-100 rounded w-full" />
                </div>
              </div>
            </div>
          ))
        ) : recommendations.length === 0 ? (
          <div className="text-center py-12">
            <TrendingUp size={26} className="mx-auto mb-3 text-gray-200" />
            <p className="text-sm text-gray-400 font-medium">No signals yet</p>
            <p className="text-xs text-gray-300 mt-1">Click REFRESH to fetch news</p>
          </div>
        ) : visible.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <p className="text-sm">No signals match filters</p>
          </div>
        ) : (
          visible.map((stock, i) => (
            <StockCard key={stock.ticker} stock={stock} rank={i + 1} />
          ))
        )}
      </div>
    </div>
  )
}
