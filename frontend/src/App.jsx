import { useState, useEffect, useCallback, useMemo } from 'react'
import Header from './components/Header'
import NewsCard from './components/NewsCard'
import StockRecommendations from './components/StockRecommendations'
import SectorHeatmap from './components/SectorHeatmap'
import SignalHistory from './components/SignalHistory'
import Analytics from './components/Analytics'
import { Newspaper, BarChart2, History, BrainCircuit } from 'lucide-react'

const LEFT_TABS = [
  { id: 'news',      label: 'News',      icon: Newspaper },
  { id: 'heatmap',   label: 'Heatmap',   icon: BarChart2 },
  { id: 'history',   label: 'History',   icon: History },
  { id: 'analytics', label: 'Analytics', icon: BrainCircuit },
]

export default function App() {
  const [news, setNews] = useState([])
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [error, setError] = useState(null)
  const [sentimentFilter, setSentimentFilter] = useState('All')
  const [urgencyFilter,   setUrgencyFilter]   = useState('All')
  const [langFilter,      setLangFilter]      = useState('All')
  const [sourceFilter,    setSourceFilter]    = useState('All')
  const [leftTab, setLeftTab] = useState('news')

  const loadData = useCallback(async () => {
    const [newsRes, recoRes] = await Promise.all([fetch('/api/news'), fetch('/api/recommendations')])
    if (!newsRes.ok || !recoRes.ok) throw new Error('Failed to fetch data from server')
    const newsData = await newsRes.json()
    const recoData = await recoRes.json()
    setNews(newsData.news || [])
    setRecommendations(recoData.recommendations || [])
    setLastUpdated(newsData.fetched_at)
  }, [])

  const fetchData = useCallback(async (forceRefresh = false) => {
    setLoading(true)
    setError(null)
    try {
      if (forceRefresh) await fetch('/api/refresh', { method: 'POST' })

      // Poll status until backend has data and is no longer refreshing
      for (let i = 0; i < 120; i++) {
        const st = await fetch('/api/status').then(r => r.json())
        if (st.has_data && !st.refresh_in_progress) break
        await new Promise(r => setTimeout(r, 3000))
      }

      await loadData()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [loadData])

  useEffect(() => { fetchData() }, [fetchData])
  useEffect(() => {
    const interval = setInterval(() => fetchData(), 10 * 60 * 1000)
    return () => clearInterval(interval)
  }, [fetchData])

  // Dynamic source list from loaded news
  const sources = useMemo(() => {
    const all = [...new Set(news.map(n => n.source_label))].sort()
    return all
  }, [news])

  const filteredNews = useMemo(() => news.filter(item => {
    if (sentimentFilter === 'Bullish'  && item.analysis?.sentiment !== 'BULLISH')  return false
    if (sentimentFilter === 'Bearish'  && item.analysis?.sentiment !== 'BEARISH')  return false
    if (sentimentFilter === 'Neutral'  && item.analysis?.sentiment !== 'NEUTRAL')  return false
    if (urgencyFilter   === 'HIGH'     && item.analysis?.urgency   !== 'HIGH')     return false
    if (urgencyFilter   === 'MEDIUM'   && item.analysis?.urgency   !== 'MEDIUM')   return false
    if (langFilter      === 'Arabic'   && item.lang !== 'ar')                       return false
    if (langFilter      === 'English'  && item.lang !== 'en')                       return false
    if (sourceFilter    !== 'All'      && item.source_label !== sourceFilter)       return false
    return true
  }), [news, sentimentFilter, urgencyFilter, langFilter, sourceFilter])

  const highUrgencyCount = news.filter(n => n.analysis?.urgency === 'HIGH').length

  const resetFilters = () => {
    setSentimentFilter('All')
    setUrgencyFilter('All')
    setLangFilter('All')
    setSourceFilter('All')
  }

  const hasActiveFilter = sentimentFilter !== 'All' || urgencyFilter !== 'All' || langFilter !== 'All' || sourceFilter !== 'All'

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header lastUpdated={lastUpdated} onRefresh={() => fetchData(true)} loading={loading} />

      <div className="flex-1 flex max-w-[1600px] mx-auto w-full px-4 md:px-6 py-5 gap-5">

        {/* LEFT panel */}
        <div className="flex-1 flex flex-col min-w-0">

          {/* Tab bar */}
          <div className="flex items-center gap-1 mb-4 bg-white border border-gray-200 rounded-xl p-1 w-fit"
            style={{boxShadow:'0 1px 3px rgba(0,0,0,0.04)'}}>
            {LEFT_TABS.map(tab => {
              const Icon = tab.icon
              const active = leftTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setLeftTab(tab.id)}
                  className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    active ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <Icon size={12} />
                  {tab.label}
                  {tab.id === 'news' && highUrgencyCount > 0 && (
                    <span className="ml-0.5 px-1.5 py-0.5 rounded-full bg-red-500 text-white text-xs font-bold leading-none">
                      {highUrgencyCount}
                    </span>
                  )}
                </button>
              )
            })}
          </div>

          {/* NEWS tab */}
          {leftTab === 'news' && (
            <>
              {/* Filter panel */}
              <div className="bg-white border border-gray-200 rounded-xl p-3 mb-4 space-y-2.5"
                style={{boxShadow:'0 1px 3px rgba(0,0,0,0.04)'}}>

                {/* Row 1: Sentiment + Urgency + Lang + clear */}
                <div className="flex items-center gap-4 flex-wrap">
                  {/* Sentiment */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-gray-400 text-xs font-medium w-16">Sentiment</span>
                    <div className="flex gap-1">
                      {['All','Bullish','Bearish','Neutral'].map(f => (
                        <button key={f} onClick={() => setSentimentFilter(f)}
                          className={`text-xs px-2.5 py-1 rounded-md font-semibold transition-all ${
                            sentimentFilter === f
                              ? f === 'Bullish' ? 'bg-emerald-600 text-white'
                              : f === 'Bearish' ? 'bg-red-500 text-white'
                              : 'bg-gray-900 text-white'
                              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                          }`}>{f}</button>
                      ))}
                    </div>
                  </div>

                  {/* Urgency */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-gray-400 text-xs font-medium w-14">Urgency</span>
                    <div className="flex gap-1">
                      {['All','HIGH','MEDIUM'].map(f => (
                        <button key={f} onClick={() => setUrgencyFilter(f)}
                          className={`text-xs px-2.5 py-1 rounded-md font-semibold transition-all ${
                            urgencyFilter === f
                              ? f === 'HIGH' ? 'bg-red-500 text-white'
                              : f === 'MEDIUM' ? 'bg-orange-500 text-white'
                              : 'bg-gray-900 text-white'
                              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                          }`}>{f}</button>
                      ))}
                    </div>
                  </div>

                  {/* Language */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-gray-400 text-xs font-medium w-12">Lang</span>
                    <div className="flex gap-1">
                      {['All','English','Arabic'].map(f => (
                        <button key={f} onClick={() => setLangFilter(f)}
                          className={`text-xs px-2.5 py-1 rounded-md font-semibold transition-all ${
                            langFilter === f ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                          }`}>{f}</button>
                      ))}
                    </div>
                  </div>

                  {/* Clear + count */}
                  <div className="ml-auto flex items-center gap-2">
                    <span className="text-gray-400 text-xs">{filteredNews.length} / {news.length}</span>
                    {hasActiveFilter && (
                      <button onClick={resetFilters}
                        className="text-xs px-2.5 py-1 rounded-md bg-gray-100 text-gray-500 hover:bg-gray-200 font-semibold">
                        Clear
                      </button>
                    )}
                  </div>
                </div>

                {/* Row 2: Source chips — dynamically from loaded news */}
                {sources.length > 0 && (
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-gray-400 text-xs font-medium w-16 flex-shrink-0">Source</span>
                    <button onClick={() => setSourceFilter('All')}
                      className={`text-xs px-2.5 py-1 rounded-md font-semibold transition-all ${
                        sourceFilter === 'All' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                      }`}>All</button>
                    {sources.map(s => (
                      <button key={s} onClick={() => setSourceFilter(s)}
                        className={`text-xs px-2.5 py-1 rounded-md font-semibold transition-all ${
                          sourceFilter === s ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                        }`}>{s}</button>
                    ))}
                  </div>
                )}
              </div>

              {error && (
                <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-xs font-medium">
                  {error} — Make sure the backend is running on port 8000.
                </div>
              )}

              <div className="overflow-y-auto flex-1">
                {loading && news.length === 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                    {Array.from({ length: 9 }).map((_, i) => (
                      <div key={i} className="rounded-xl border border-gray-200 bg-white p-4 animate-pulse">
                        <div className="flex gap-2 mb-3">
                          <div className="h-4 w-20 bg-gray-100 rounded-md" />
                          <div className="h-4 w-14 bg-gray-100 rounded-md" />
                        </div>
                        <div className="h-4 bg-gray-100 rounded w-full mb-2" />
                        <div className="h-3 bg-gray-100 rounded w-3/4" />
                      </div>
                    ))}
                  </div>
                ) : filteredNews.length === 0 && !loading ? (
                  <div className="text-center py-16 text-gray-400">
                    <Newspaper size={28} className="mx-auto mb-3 opacity-20" />
                    <p className="text-sm">No news for this filter</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                    {filteredNews.map(item => <NewsCard key={item.id} item={item} />)}
                  </div>
                )}
              </div>
            </>
          )}

          {/* HEATMAP tab */}
          {leftTab === 'heatmap' && <SectorHeatmap />}

          {/* HISTORY tab */}
          {leftTab === 'history' && <SignalHistory />}

          {/* ANALYTICS tab */}
          {leftTab === 'analytics' && <Analytics />}
        </div>

        {/* RIGHT: sticky signals sidebar */}
        <div className="w-[340px] flex-shrink-0 hidden lg:flex flex-col sticky top-[65px] h-[calc(100vh-65px-40px)]">
          <StockRecommendations
            recommendations={recommendations}
            loading={loading && recommendations.length === 0}
          />
        </div>
      </div>

      {/* Mobile signals */}
      <div className="lg:hidden px-4 pb-6">
        <StockRecommendations
          recommendations={recommendations}
          loading={loading && recommendations.length === 0}
        />
      </div>
    </div>
  )
}
