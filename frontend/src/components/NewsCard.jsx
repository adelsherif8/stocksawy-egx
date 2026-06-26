import { useState } from 'react'
import { ExternalLink, ChevronDown, ChevronUp, TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react'

const SENTIMENT_CONFIG = {
  BULLISH: { color: 'text-emerald-600', bg: 'bg-emerald-50',  border: 'border-emerald-200', label: 'Bullish',  icon: TrendingUp },
  BEARISH: { color: 'text-red-500',     bg: 'bg-red-50',      border: 'border-red-200',     label: 'Bearish',  icon: TrendingDown },
  NEUTRAL: { color: 'text-gray-500',    bg: 'bg-gray-100',    border: 'border-gray-200',    label: 'Neutral',  icon: Minus },
}

const URGENCY_CONFIG = {
  HIGH:   { color: 'text-red-600',    bg: 'bg-red-50',    border: 'border-red-200',    label: 'URGENT' },
  MEDIUM: { color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200', label: 'MEDIUM' },
  LOW:    { color: 'text-gray-400',   bg: 'bg-gray-50',   border: 'border-gray-200',   label: 'LOW' },
}

const ACTION_MINI = {
  BUY:   { color: 'text-emerald-700', bg: 'bg-emerald-50',  border: 'border-emerald-200' },
  SELL:  { color: 'text-red-600',     bg: 'bg-red-50',      border: 'border-red-200' },
  WATCH: { color: 'text-orange-600',  bg: 'bg-orange-50',   border: 'border-orange-200' },
}

const LABEL_COLORS = {
  'EGX Market':                  'bg-gray-900 text-white',
  'Egypt Economy':               'bg-teal-600 text-white',
  'Egypt Currency':              'bg-gray-600 text-white',
  'Oil & Gas':                   'bg-orange-600 text-white',
  'Geopolitics':                 'bg-red-600 text-white',
  'Global Markets':              'bg-blue-600 text-white',
  'Suez Canal':                  'bg-cyan-700 text-white',
  'Commodities':                 'bg-yellow-600 text-white',
  'Gold & Inflation':            'bg-amber-600 text-white',
  'Egypt Tourism & Real Estate': 'bg-rose-600 text-white',
}

export default function NewsCard({ item }) {
  const [expanded, setExpanded] = useState(false)
  const analysis = item.analysis || {}
  const sentiment = SENTIMENT_CONFIG[analysis.sentiment] || SENTIMENT_CONFIG.NEUTRAL
  const urgency = URGENCY_CONFIG[analysis.urgency] || URGENCY_CONFIG.LOW
  const SentimentIcon = sentiment.icon
  const affectedStocks = analysis.affected_stocks || []
  const isHighUrgency = analysis.urgency === 'HIGH'
  const labelClass = LABEL_COLORS[item.source_label] || 'bg-gray-700 text-white'

  return (
    <div
      className={`slide-in rounded-xl bg-white transition-all ${
        isHighUrgency
          ? 'border border-red-300 shadow-sm shadow-red-100'
          : 'border border-gray-200'
      }`}
      style={{boxShadow: isHighUrgency ? '0 1px 4px rgba(239,68,68,0.1)' : '0 1px 3px rgba(0,0,0,0.04)'}}
    >
      <div className="p-4">
        {/* Top row */}
        <div className="flex items-center gap-2 mb-2.5 flex-wrap">
          <span className={`text-xs px-2 py-0.5 rounded-md font-bold tracking-wide ${labelClass}`}>
            {item.source_label}
          </span>

          {analysis.urgency && analysis.urgency !== 'LOW' && (
            <span className={`flex items-center gap-0.5 text-xs px-2 py-0.5 rounded-md font-bold border ${urgency.bg} ${urgency.color} ${urgency.border}`}>
              {isHighUrgency && <AlertTriangle size={9} className="mr-0.5" />}
              {urgency.label}
            </span>
          )}

          {analysis.sentiment && (
            <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-md font-semibold border ${sentiment.bg} ${sentiment.color} ${sentiment.border}`}>
              <SentimentIcon size={10} />
              {sentiment.label}
            </span>
          )}

          <span className="text-gray-400 text-xs font-mono ml-auto">{item.published}</span>
        </div>

        {/* Title — clickable link */}
        <a
          href={item.link}
          target="_blank"
          rel="noopener noreferrer"
          className="group flex items-start gap-1 mb-2"
        >
          <h3 className="text-gray-900 font-semibold text-sm leading-snug group-hover:text-blue-600 transition-colors">
            {item.title}
          </h3>
          <ExternalLink size={11} className="text-gray-300 group-hover:text-blue-400 transition-colors flex-shrink-0 mt-0.5" />
        </a>

        {/* AI Impact */}
        {analysis.impact_summary && (
          <p className="text-gray-500 text-xs leading-relaxed mb-3 pl-2 border-l-2 border-gray-200">{analysis.impact_summary}</p>
        )}

        {/* Stock pills */}
        {affectedStocks.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {affectedStocks.slice(0, expanded ? affectedStocks.length : 4).map(s => {
              const cfg = ACTION_MINI[s.action] || ACTION_MINI.WATCH
              const stockUrl = `https://www.tradingview.com/symbols/EGX-${s.ticker}/`
              const alreadyMoved = s.already_moved
              const livePrice = s.price_data?.available ? s.price_data : null
              return (
                <div key={s.ticker} className="flex flex-col gap-1">
                  <a
                    href={stockUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-semibold transition-opacity hover:opacity-75 ${cfg.bg} ${cfg.color} ${cfg.border}`}
                  >
                    <span className="font-mono font-bold">{s.ticker}</span>
                    <span className="opacity-60">·</span>
                    <span>{s.action}</span>
                    {s.expected_change && <span className="font-mono font-bold">{s.expected_change}</span>}
                    {livePrice && (
                      <span className="font-mono opacity-75">
                        EGP {livePrice.price} ({livePrice.change_pct >= 0 ? '+' : ''}{livePrice.change_pct}%)
                      </span>
                    )}
                    <ExternalLink size={9} className="opacity-50" />
                  </a>
                  {alreadyMoved && (
                    <span className="flex items-center gap-1 text-xs text-orange-600 bg-orange-50 border border-orange-200 px-2 py-0.5 rounded-md font-semibold w-fit">
                      ⚠ Already moved {s.moved_pct >= 0 ? '+' : ''}{s.moved_pct}% — possibly priced in
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* Footer */}
        {affectedStocks.length > 0 && (
          <div className="flex items-center justify-end pt-2 border-t border-gray-100">
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-700 transition-colors"
            >
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {expanded ? 'Show less' : `${affectedStocks.length} stocks`}
            </button>
          </div>
        )}

        {/* Expanded detail */}
        {expanded && affectedStocks.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
            {affectedStocks.map(s => {
              const cfg = ACTION_MINI[s.action] || ACTION_MINI.WATCH
              const stockUrl = `https://www.tradingview.com/symbols/EGX-${s.ticker}/`
              return (
                <div key={s.ticker} className="flex items-start gap-2.5">
                  <a
                    href={stockUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`font-mono text-xs font-bold w-14 flex-shrink-0 hover:underline ${cfg.color}`}
                  >
                    {s.ticker}
                  </a>
                  <span className="text-gray-500 text-xs leading-relaxed">{s.reason}</span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
