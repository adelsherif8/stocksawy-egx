import { useEffect, useState } from 'react'
import { RefreshCw, TrendingUp, Target, Activity, Zap, FlaskConical } from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell, ReferenceLine, Legend
} from 'recharts'

const CONF_COLORS   = { HIGH: '#10b981', MEDIUM: '#f59e0b', LOW: '#6b7280' }
const HORIZON_COLORS = { 'Since signal': '#a855f7', 'Next day': '#60a5fa', '5 days': '#818cf8' }

function StatCard({ label, value, sub, color = 'text-gray-800' }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-3" style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
      <p className="text-gray-400 text-[10px] mb-0.5">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value ?? '—'}</p>
      {sub && <p className="text-gray-300 text-[10px] mt-0.5">{sub}</p>}
    </div>
  )
}

function SectionTitle({ icon: Icon, title, sub }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <Icon size={14} className="text-purple-500 flex-shrink-0" />
      <div>
        <p className="text-xs font-bold text-gray-700">{title}</p>
        {sub && <p className="text-[10px] text-gray-400">{sub}</p>}
      </div>
    </div>
  )
}

const TT = ({ active, payload, label, suffix = '%' }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 shadow-md text-xs">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.value != null ? `${p.value}${suffix}` : 'N/A'}
        </p>
      ))}
    </div>
  )
}

export default function Analytics() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [runMsg, setRunMsg]   = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/backtest/stats')
      setData(await res.json())
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const runBacktest = async () => {
    setRunning(true)
    setRunMsg('Running backtest against historical prices…')
    try {
      await fetch('/api/backtest/run', { method: 'POST' })
      // Poll until data appears (up to 3 min)
      for (let i = 0; i < 36; i++) {
        await new Promise(r => setTimeout(r, 5000))
        const res = await fetch('/api/backtest/stats')
        const d = await res.json()
        if (d.available > 0) {
          setData(d)
          setRunMsg(`Done — ${d.available} signals evaluated`)
          break
        }
        setRunMsg(`Fetching prices… (${(i + 1) * 5}s)`)
      }
    } catch (e) { setRunMsg('Error running backtest') }
    finally { setRunning(false) }
  }

  useEffect(() => { load() }, [])

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw size={24} className="mx-auto mb-3 text-gray-300 animate-spin" />
          <p className="text-sm text-gray-400">Loading…</p>
        </div>
      </div>
    )
  }

  const noData = !data || !data.ready || data.available === 0

  return (
    <div className="flex flex-col gap-5 pb-6 overflow-y-auto">

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-gray-800 font-semibold text-sm">AI Performance Backtest</h2>
          <p className="text-gray-400 text-xs mt-0.5">
            {data?.available
              ? `${data.available} signals evaluated against real EGX prices`
              : 'Run a backtest to evaluate AI predictions against historical prices'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="p-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors">
            <RefreshCw size={12} className="text-gray-500" />
          </button>
          <button
            onClick={runBacktest}
            disabled={running}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg font-semibold transition-all ${
              running
                ? 'bg-purple-100 text-purple-400 cursor-not-allowed'
                : 'bg-purple-600 text-white hover:bg-purple-700'
            }`}
          >
            <FlaskConical size={11} />
            {running ? 'Running…' : data?.available ? 'Re-run Backtest' : 'Run Backtest'}
          </button>
        </div>
      </div>

      {/* Status message */}
      {runMsg && (
        <div className={`text-xs px-3 py-2 rounded-lg font-medium ${
          running ? 'bg-purple-50 text-purple-600 border border-purple-200'
                  : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
        }`}>
          {running && <RefreshCw size={10} className="inline mr-1.5 animate-spin" />}
          {runMsg}
        </div>
      )}

      {noData ? (
        <div className="flex-1 flex items-center justify-center py-16">
          <div className="text-center">
            <FlaskConical size={32} className="mx-auto mb-3 text-gray-200" />
            <p className="text-sm text-gray-500 font-medium">No backtest results yet</p>
            <p className="text-xs text-gray-400 mt-1 mb-4">
              Click "Run Backtest" to evaluate all AI predictions against real EGX historical prices.
            </p>
            <button
              onClick={runBacktest}
              disabled={running}
              className="flex items-center gap-1.5 text-xs px-4 py-2 rounded-lg font-semibold bg-purple-600 text-white hover:bg-purple-700 mx-auto transition-all disabled:opacity-50"
            >
              <FlaskConical size={12} />
              {running ? 'Running…' : 'Run Backtest Now'}
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Top stat cards */}
          <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
            <StatCard label="Live Acc"   value={data.accuracy_now != null ? `${data.accuracy_now}%` : null} color="text-purple-600" sub={`${data.total_resolved_now || 0} signals`} />
            <StatCard label="1-Day Acc"  value={data.accuracy_1d  != null ? `${data.accuracy_1d}%`  : null} color="text-blue-500"   sub={`${data.total_resolved_1d || 0} resolved`} />
            <StatCard label="5-Day Acc"  value={data.accuracy_5d  != null ? `${data.accuracy_5d}%`  : null} color="text-indigo-500" sub={`${data.total_resolved_5d || 0} resolved`} />
            <StatCard label="BUY Acc"    value={data.accuracy_action_BUY  != null ? `${data.accuracy_action_BUY}%`  : null} color="text-emerald-600" />
            <StatCard label="SELL Acc"   value={data.accuracy_action_SELL != null ? `${data.accuracy_action_SELL}%` : null} color="text-red-500" />
            <StatCard label="Evaluated"  value={data.available} color="text-gray-700" sub="signals with price data" />
          </div>

          {/* Row 1: Accuracy over time + Horizon comparison */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">

            <div className="bg-white rounded-xl border border-gray-200 p-4" style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
              <SectionTitle icon={Activity} title="Accuracy Over Time" sub="Live win rate by article date" />
              {data.accuracy_over_time?.length >= 1 ? (
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={data.accuracy_over_time} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#9ca3af' }} tickFormatter={v => v.slice(5)} />
                    <YAxis tick={{ fontSize: 9, fill: '#9ca3af' }} domain={[0, 100]} />
                    <Tooltip content={<TT suffix="%" />} />
                    <ReferenceLine y={50} stroke="#e5e7eb" strokeDasharray="4 4" />
                    <Line type="monotone" dataKey="accuracy" name="Win rate" stroke="#a855f7" strokeWidth={2}
                      dot={{ r: 4, fill: '#a855f7' }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[180px] flex items-center justify-center text-xs text-gray-300">Need more data points</div>
              )}
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-4" style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
              <SectionTitle icon={Zap} title="Live vs 1-Day vs 5-Day" sub="Is the AI better short or long term?" />
              {data.horizon_chart?.some(h => h.accuracy != null) ? (
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={data.horizon_chart} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="horizon" tick={{ fontSize: 10, fill: '#9ca3af' }} />
                    <YAxis tick={{ fontSize: 9, fill: '#9ca3af' }} domain={[0, 100]} />
                    <Tooltip content={<TT suffix="%" />} />
                    <ReferenceLine y={50} stroke="#e5e7eb" strokeDasharray="4 4" />
                    <Bar dataKey="accuracy" name="Accuracy" radius={[4, 4, 0, 0]}>
                      {data.horizon_chart.map(h => (
                        <Cell key={h.horizon} fill={HORIZON_COLORS[h.horizon] || '#9ca3af'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[180px] flex items-center justify-center text-xs text-gray-300">No resolved signals yet</div>
              )}
            </div>
          </div>

          {/* Row 2: Sector accuracy + Confidence calibration */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">

            <div className="bg-white rounded-xl border border-gray-200 p-4" style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
              <SectionTitle icon={TrendingUp} title="Sector Accuracy" sub="5-day win rate by sector (min 2 signals)" />
              {data.sector_chart?.length > 0 ? (
                <ResponsiveContainer width="100%" height={Math.max(160, data.sector_chart.length * 32)}>
                  <BarChart data={data.sector_chart} layout="vertical" margin={{ top: 4, right: 40, bottom: 4, left: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                    <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 9, fill: '#9ca3af' }} />
                    <YAxis type="category" dataKey="sector" tick={{ fontSize: 9, fill: '#6b7280' }} width={100} />
                    <Tooltip formatter={(v, _n, p) => [`${v}% (${p.payload.signals} signals)`, 'Accuracy']}
                      contentStyle={{ fontSize: 11 }} />
                    <ReferenceLine x={50} stroke="#e5e7eb" strokeDasharray="4 4" />
                    <Bar dataKey="accuracy" name="Accuracy" radius={[0, 4, 4, 0]}>
                      {data.sector_chart.map((s, i) => (
                        <Cell key={i} fill={s.accuracy >= 60 ? '#10b981' : s.accuracy >= 40 ? '#f59e0b' : '#ef4444'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[160px] flex items-center justify-center text-xs text-gray-300">Need ≥ 2 signals per sector</div>
              )}
              {data.best_sector && (
                <div className="flex gap-4 mt-3 pt-3 border-t border-gray-100 text-xs">
                  <div>
                    <span className="text-gray-400">Best: </span>
                    <span className="font-bold text-emerald-600">{data.best_sector.name} · {data.best_sector.accuracy}%</span>
                  </div>
                  {data.worst_sector && (
                    <div>
                      <span className="text-gray-400">Worst: </span>
                      <span className="font-bold text-red-500">{data.worst_sector.name} · {data.worst_sector.accuracy}%</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-4" style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
              <SectionTitle icon={Target} title="Confidence Calibration" sub="Does HIGH confidence = higher accuracy?" />
              {data.confidence_chart?.length > 0 ? (
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={data.confidence_chart} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="confidence" tick={{ fontSize: 10, fill: '#9ca3af' }} />
                    <YAxis tick={{ fontSize: 9, fill: '#9ca3af' }} domain={[0, 100]} />
                    <Tooltip
                      formatter={(v, _n, p) => [
                        `${v}% (${p.payload.total} signals: ${p.payload.wins}W / ${p.payload.losses}L)`,
                        'Accuracy'
                      ]}
                      contentStyle={{ fontSize: 11 }}
                    />
                    <ReferenceLine y={50} stroke="#e5e7eb" strokeDasharray="4 4" />
                    <Bar dataKey="accuracy" name="Accuracy" radius={[4, 4, 0, 0]}>
                      {data.confidence_chart.map(c => (
                        <Cell key={c.confidence} fill={CONF_COLORS[c.confidence] || '#9ca3af'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[180px] flex items-center justify-center text-xs text-gray-300">No resolved signals yet</div>
              )}
            </div>
          </div>

          {/* Row 3: BUY/SELL breakdown + Scatter */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">

            <div className="bg-white rounded-xl border border-gray-200 p-4" style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
              <SectionTitle icon={Zap} title="BUY vs SELL Breakdown" sub="Wins / Losses / Evens per action type" />
              {data.action_chart?.length > 0 ? (
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={data.action_chart} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="action" tick={{ fontSize: 10, fill: '#9ca3af' }} />
                    <YAxis tick={{ fontSize: 9, fill: '#9ca3af' }} />
                    <Tooltip contentStyle={{ fontSize: 11 }} />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Bar dataKey="wins"   name="Wins"   stackId="a" fill="#10b981" />
                    <Bar dataKey="losses" name="Losses" stackId="a" fill="#ef4444" />
                    <Bar dataKey="evens"  name="Evens"  stackId="a" fill="#e5e7eb" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[180px] flex items-center justify-center text-xs text-gray-300">No resolved signals yet</div>
              )}
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-4" style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
              <SectionTitle icon={Target} title="Predicted vs Actual Move" sub="Dots near the diagonal = accurate AI · current price vs entry" />
              {data.scatter?.length > 0 ? (
                <ResponsiveContainer width="100%" height={180}>
                  <ScatterChart margin={{ top: 4, right: 8, bottom: 16, left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="predicted" name="Predicted" type="number" tick={{ fontSize: 9, fill: '#9ca3af' }}
                      label={{ value: 'Predicted %', position: 'insideBottom', offset: -8, fontSize: 9, fill: '#9ca3af' }} />
                    <YAxis dataKey="actual" name="Actual" type="number" tick={{ fontSize: 9, fill: '#9ca3af' }} />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }}
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null
                        const d = payload[0]?.payload
                        if (!d) return null
                        return (
                          <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 shadow-md text-xs">
                            <p className="font-bold text-gray-700">{d.ticker} · {d.action}</p>
                            <p className="text-purple-600">Predicted: {d.predicted}%</p>
                            <p className={d.actual >= 0 ? 'text-emerald-600' : 'text-red-500'}>
                              Actual (5d): {d.actual != null ? `${d.actual > 0 ? '+' : ''}${d.actual?.toFixed(1)}%` : 'N/A'}
                            </p>
                            <p className="text-gray-400">{d.outcome}</p>
                          </div>
                        )
                      }}
                    />
                    <ReferenceLine x={0} stroke="#e5e7eb" />
                    <ReferenceLine y={0} stroke="#e5e7eb" />
                    <Scatter data={data.scatter}>
                      {data.scatter.map((s, i) => (
                        <Cell key={i}
                          fill={s.outcome === 'WIN' ? '#10b981' : s.outcome === 'LOSS' ? '#ef4444' : '#d1d5db'}
                          fillOpacity={0.7}
                        />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[180px] flex items-center justify-center text-xs text-gray-300">No predicted vs actual data</div>
              )}
              <div className="flex gap-4 mt-2 text-[10px] text-gray-400">
                <span><span className="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1" />WIN</span>
                <span><span className="inline-block w-2 h-2 rounded-full bg-red-400 mr-1" />LOSS</span>
                <span><span className="inline-block w-2 h-2 rounded-full bg-gray-300 mr-1" />EVEN</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
