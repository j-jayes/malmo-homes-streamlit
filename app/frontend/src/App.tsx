import { useEffect, useState } from 'react';
import { Map } from './components/Map';
import { Filters } from './components/Filters';
import { BestDeals } from './components/BestDeals';
import { ActiveListingsPanel } from './components/ActiveListingsPanel';
import { PropertyDetailModal } from './components/PropertyDetailModal';
import { InsightsPanel } from './components/InsightsPanel';
import { api } from './api/client';
import type { PropertyWithPrediction, ActiveListing, PropertyStats, Filters as FilterType } from './api/client';
import { Building2, TrendingUp, BarChart2, Home, Layers, BookOpen } from 'lucide-react';

type ViewMode = 'sold' | 'active' | 'insights';

function StatPill({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-slate-500 bg-slate-50 border border-slate-100 rounded-full px-3 py-1 shrink-0">
      <span className="text-slate-400">{icon}</span>
      <span className="text-slate-400 hidden sm:inline">{label}</span>
      <span className="font-semibold text-slate-700">{value}</span>
    </div>
  );
}

function App() {
  const [properties, setProperties] = useState<PropertyWithPrediction[]>([]);
  const [activeListings, setActiveListings] = useState<ActiveListing[]>([]);
  const [deals, setDeals] = useState<PropertyWithPrediction[]>([]);
  const [stats, setStats] = useState<PropertyStats | null>(null);
  const [filters, setFilters] = useState<FilterType>({});
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewMode>('sold');
  const [selectedListing, setSelectedListing] = useState<ActiveListing | null>(null);
  const [insightAnchor, setInsightAnchor] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [propsData, statsData, dealsData, activeData] = await Promise.all([
          api.getPropertiesWithPredictions(filters),
          api.getStats(),
          api.getDeals(10),
          api.getActiveListings(filters),
        ]);
        setProperties(propsData);
        setStats(statsData);
        setDeals(dealsData);
        setActiveListings(activeData);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [filters]);

  const openInsight = (anchor: string) => {
    setSelectedListing(null);
    setView('insights');
    setInsightAnchor(anchor);
  };

  const avgM = stats ? (stats.avg_price / 1_000_000).toFixed(1) + 'M' : '—';
  const avgSqm = stats ? Math.round(stats.avg_price_per_sqm).toLocaleString('sv-SE') : '—';

  return (
    <div className="h-full flex flex-col bg-canvas">
      {/* ─── Header ─────────────────────────────────────────────────── */}
      <header className="h-13 shrink-0 bg-white border-b border-slate-100 flex items-center px-4 gap-3 z-40" style={{ height: '52px' }}>
        {/* Logo */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="w-7 h-7 bg-brand-600 rounded-lg flex items-center justify-center shadow-sm">
            <Home className="text-white w-4 h-4" strokeWidth={2.5} />
          </div>
          <span className="font-semibold text-slate-900 text-sm tracking-tight">Malmö Homes</span>
        </div>

        <div className="w-px h-5 bg-slate-100 shrink-0 mx-1" />

        {/* Inline stats */}
        <div className="flex items-center gap-2 flex-1 overflow-hidden">
          {stats && (
            <>
              <StatPill icon={<Building2 size={12} />} label="sold" value={stats.total_properties.toLocaleString()} />
              <StatPill icon={<Layers size={12} />} label="for sale" value={(stats.active_listings_count ?? 0).toLocaleString()} />
              <StatPill icon={<TrendingUp size={12} />} label="avg" value={avgM + ' kr'} />
              <StatPill icon={<BarChart2 size={12} />} label="avg/m²" value={avgSqm + ' kr'} />
              {stats.model_avg_error_pct != null && (
                <StatPill icon={<span className="text-[10px] font-bold">ML</span>} label="error" value={'±' + stats.model_avg_error_pct + '%'} />
              )}
            </>
          )}
        </div>

        {/* View toggle */}
        <div className="flex bg-slate-100 rounded-lg p-0.5 shrink-0 gap-0.5">
          <button
            onClick={() => setView('sold')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              view === 'sold'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Sold
            <span className="ml-1.5 text-[10px] tabular-nums opacity-60">{properties.length}</span>
          </button>
          <button
            onClick={() => setView('active')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              view === 'active'
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            For Sale
            <span className="ml-1.5 text-[10px] tabular-nums opacity-60">{activeListings.length}</span>
          </button>
          <button
            onClick={() => setView('insights')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              view === 'insights'
                ? 'bg-violet-600 text-white shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <BookOpen size={11} />
            Insights
          </button>
        </div>
      </header>

      {/* ─── Body ────────────────────────────────────────────────────── */}
      {view === 'insights' ? (
        <InsightsPanel
          anchor={insightAnchor}
          onAnchorConsumed={() => setInsightAnchor(null)}
        />
      ) : (
        <div className="flex-1 flex overflow-hidden">
          {/* Sidebar */}
          <aside className="w-72 xl:w-80 shrink-0 bg-white border-r border-slate-100 flex flex-col overflow-hidden shadow-panel z-30">
            {/* Filters */}
            <div className="shrink-0 px-4 pt-4 pb-3 border-b border-slate-100">
              <Filters filters={filters} onChange={setFilters} />
            </div>

            {/* Section header */}
            <div className="shrink-0 px-4 pt-3 pb-2 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                {view === 'sold' ? 'Best Deals' : 'For Sale Now'}
              </span>
              <span className="text-xs text-slate-400 tabular-nums">
                {view === 'sold' ? deals.length : activeListings.length}
              </span>
            </div>

            {/* Scrollable feed */}
            <div className="flex-1 overflow-y-auto sidebar-scroll px-3 pb-4">
              {view === 'sold' ? (
                <BestDeals deals={deals} loading={loading} />
              ) : (
                <ActiveListingsPanel
                  listings={activeListings}
                  loading={loading}
                  onSelect={setSelectedListing}
                />
              )}
            </div>
          </aside>

          {/* Map panel */}
          <main className="flex-1 relative overflow-hidden">
            {loading ? (
              <div className="absolute inset-0 bg-slate-50 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                  <div className="w-8 h-8 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs text-slate-400">Loading map data…</span>
                </div>
              </div>
            ) : (
              <Map
                properties={properties}
                activeListings={activeListings}
                view={view as 'sold' | 'active'}
              />
            )}
          </main>
        </div>
      )}

      {/* Detail modal */}
      {selectedListing && (
        <PropertyDetailModal
          listing={selectedListing}
          onClose={() => setSelectedListing(null)}
          onOpenInsight={openInsight}
        />
      )}
    </div>
  );
}

export default App;
