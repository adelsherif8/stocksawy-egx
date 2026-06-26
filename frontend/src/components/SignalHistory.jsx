import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Minus, RefreshCw, Clock, Brain } from 'lucide-react'

const ACTION_CFG = {
  BUY:   { color: 'text-emerald-700', bg: 'bg-emerald-600', icon: TrendingUp },
  SELL:  { color: 'text-red-600',     bg: 'bg-red-500',     icon: TrendingDown },
  WATCH: { color: 'text-orange-600',  bg: 'bg-orange-500',  icon: Minus },
}

const OUTCOME_STYLE = {
  WIN:     'text-emerald-700 bg-emerald-50 border-emerald-200',
  LOSS:    'text-red-600 bg-red-50 border-red-200',
  EVEN:    'text-gray-500 bg-gray-50 border-gray-200',
  PENDING: 'text-blue-400 bg-blue-50 border-blue-200',
  NO_DATA: 'text-gray-300 bg-gray-50 border-gray-100',
}
const OUTCOME_LABEL = { WIN: '✅ WIN', LOSS: '❌ LOSS', EVEN: '➡️ EVEN', PENDING: '⏳ —', NO_DATA: 'N/A' }

function CheckpointBadge({ outcome, actual, predicted, label }) {
  const style = OUTCOME_STYLE[outcome] || OUTCOME_STYLE.PENDING
  const text  = OUTCOME_LABEL[outcome] || '⏳'
  return (
    <div className={`flex flex-col items-center px-2 py-1 rounded-lg border text-center min-w-[56px] ${style}`}>
      <span className="text-[10px] font-bold opacity-60 mb-0.5">{label}</span>
      <span className="text-xs font-bold leading-none">{text}</span>
      {actual != null && (
        <span className={`text-[10px] mt-0.5 font-mono ${actual >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
          {actual >= 0 ? '+' : ''}{actual.toFixed(1)}%
        </span>
      )}
    </div>
  )
}

function SignalRow({ sig }) {
  const action = ACTION_CFG[sig.action] || ACTION_CFG.WATCH
  const ActionIcon = action.icon

  return (
    <div className="py-3 border-b border-gray-100 last:border-0">
      <div className="flex items-start gap-3">
        {/* Action icon */}
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${action.bg}`}>
          <ActionIcon size={13} className="text-white" />
        </div>

        {/* Ticker + info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <a href={`https://www.tradingview.com/symbols/EGX-${sig.ticker}/`}
              target="_blank" rel="noopener noreferrer"
              className={`font-mono font-bold text-sm hover:underline ${action.color}`}>
              {sig.ticker}
            </a>
            <span className="text-gray-400 text-xs truncate">{sig.name}</span>
            <span className="text-gray-300 text-xs">·</span>
            {sig.price_at_signal ? (
              <span className="text-gray-500 text-xs font-mono">Entry EGP {sig.price_at_signal}</span>
            ) : (
              <span className="text-gray-300 text-xs">no price data</span>
            )}
            {sig.expected_change && (
              <span className="text-xs text-purple-500 font-semibold">AI: {sig.expected_change}</span>
            )}
          </div>
          <p className="text-gray-400 text-xs mt-0.5 truncate">{sig.reason}</p>
          <p className="text-gray-300 text-xs mt-0.5">{sig.date}</p>
        </div>

        {/* 3 checkpoint badges */}
        <div className="flex gap-1.5 flex-shrink-0">
          <CheckpointBadge label="1h"  outcome={sig.outcome_1h}  actual={sig.change_1h}  />
          <CheckpointBadge label="6h"  outcome={sig.outcome_6h}  actual={sig.change_6h}  />
          <CheckpointBadge label="24h" outcome={sig.outcome_24h} actual={sig.change_24h} />
        </div>
      </div>
    </div>
  )
}

function AccuracyBar({ label, value, color }) {
  if (value == null) return null
  return (
    <div className="flex items-center gap-2">
      <span className="text-gray-400 text-xs w-20 flex-shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-xs font-bold text-gray-700 w-10 text-right">{value}%</span>
    </div>
  )
}

const FILTERS = ['All', 'Resolved', 'Pending']

export default function SignalHistory() {
  const [signals, setSignals]     = useState([])
  const [stats, setStats]         = useState(null)
  const [learning, setLearning]   = useState(null)
  const [loading, setLoading]     = useState(true)
  const [filter, setFilter]       = useState('All')
  const [showLearning, setShowLearning] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [histRes, learnRes] = await Promise.all([
        fetch('/api/history'),
        fetch('/api/learning'),
      ])
      const histJson  = await histRes.json()
      const learnJson = await learnRes.json()
      setSignals(histJson.signals || [])
      setStats(histJson.stats || null)
      setLearning(learnJson)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = signals.filter(s => {
    if (filter === 'Resolved') return ['WIN','LOSS','EVEN'].includes(s.outcome_24h)
    if (filter === 'Pending')  return s.outcome_24h === 'PENDING'
    return s.outcome !== 'NO_DATA'
  })

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-gray-800 font-semibold text-sm">Signal History</h2>
          <p className="text-gray-400 text-xs mt-0.5">1h · 6h · 24h outcome tracking</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowLearning(v => !v)}
            className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg font-semibold transition-all ${
              showLearning ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}>
            <Brain size={11} />AI Stats
          </button>
          <div className="flex gap-0.5 bg-gray-100 rounded-lg p-0.5">
            {FILTERS.map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={`text-xs px-2.5 py-1 rounded-md font-semibold transition-all ${
                  filter === f ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-400 hover:text-gray-600'
                }`}>{f}</button>
            ))}
          </div>
          <button onClick={load} className="p-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors">
            <RefreshCw size={12} className={`text-gray-500 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Stats row */}
      {stats && (
        <div className="grid grid-cols-5 gap-2 mb-3">
          {[
            { label: '1h Acc',  value: stats.accuracy_1h,  color: 'text-blue-500' },
            { label: '6h Acc',  value: stats.accuracy_6h,  color: 'text-indigo-500' },
            { label: '24h Acc', value: stats.accuracy_24h, color: 'text-purple-600' },
            { label: 'Wins',    value: stats.wins,          color: 'text-emerald-600', raw: true },
            { label: 'Pending', value: stats.pending,       color: 'text-blue-400',    raw: true },
          ].map(({ label, value, color, raw }) => (
            <div key={label} className="bg-white rounded-xl border border-gray-200 p-2.5" style={{boxShadow:'0 1px 3px rgba(0,0,0,0.04)'}}>
              <p className="text-gray-400 text-[10px] mb-0.5">{label}</p>
              <p className={`text-xl font-bold ${color}`}>{value != null ? (raw ? value : `${value}%`) : '—'}</p>
            </div>
          ))}
        </div>
      )}

      {/* Learning panel */}
      {showLearning && learning && (
        <div className="bg-white border border-purple-100 rounded-xl p-4 mb-3 space-y-2"
          style={{boxShadow:'0 1px 3px rgba(0,0,0,0.04)'}}>
          <div className="flex items-center gap-2 mb-2">
            <Brain size={13} className="text-purple-500" />
            <span className="text-xs font-bold text-purple-700">AI Self-Learning Stats</span>
            <span className="text-xs text-gray-400 ml-auto">{learning.total_signals} total signals</span>
          </div>
          <AccuracyBar label="1h accuracy"  value={learning.accuracy_1h}  color="bg-blue-400" />
          <AccuracyBar label="6h accuracy"  value={learning.accuracy_6h}  color="bg-indigo-400" />
          <AccuracyBar label="24h accuracy" value={learning.accuracy_24h} color="bg-purple-500" />
          <AccuracyBar label="BUY signals"  value={learning.accuracy_action_BUY}  color="bg-emerald-400" />
          <AccuracyBar label="SELL signals" value={learning.accuracy_action_SELL} color="bg-red-400" />
          <AccuracyBar label="HIGH conf"    value={learning.accuracy_confidence_HIGH}   color="bg-emerald-500" />
          <AccuracyBar label="MED conf"     value={learning.accuracy_confidence_MEDIUM} color="bg-yellow-400" />

          {learning.best_sector && (
            <div className="flex gap-4 pt-1 border-t border-gray-100 mt-1">
              <div>
                <span className="text-[10px] text-gray-400">Best sector</span>
                <p className="text-xs font-bold text-emerald-600">{learning.best_sector.name} · {learning.best_sector.accuracy}%</p>
              </div>
              {learning.worst_sector && (
                <div>
                  <span className="text-[10px] text-gray-400">Weakest sector</span>
                  <p className="text-xs font-bold text-red-500">{learning.worst_sector.name} · {learning.worst_sector.accuracy}%</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Signal list */}
      <div className="flex-1 overflow-y-auto bg-white rounded-xl border border-gray-200 px-4"
        style={{boxShadow:'0 1px 3px rgba(0,0,0,0.04)'}}>
        {loading ? (
          <div className="space-y-3 py-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 animate-pulse">
                <div className="w-8 h-8 rounded-lg bg-gray-100" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-3 bg-gray-100 rounded w-1/4" />
                  <div className="h-3 bg-gray-100 rounded w-1/2" />
                </div>
                <div className="flex gap-1.5">
                  {[0,1,2].map(j => <div key={j} className="h-10 w-14 bg-gray-100 rounded-lg" />)}
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12">
            <Clock size={28} className="mx-auto mb-3 text-gray-200" />
            <p className="text-sm text-gray-400 font-medium">
              {filter === 'Resolved' ? 'No resolved signals yet' : 'No signals logged yet'}
            </p>
            <p className="text-xs text-gray-300 mt-1">
              {filter === 'Resolved' ? 'Outcomes appear after 1h, 6h, and 24h' : 'Signals appear after the first refresh'}
            </p>
          </div>
        ) : (
          filtered.map(sig => <SignalRow key={sig.signal_key || sig.id} sig={sig} />)
        )}
      </div>
    </div>
  )
}
