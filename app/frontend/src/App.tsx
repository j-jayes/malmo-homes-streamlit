import { useEffect, useState } from 'react';
import { Map } from './components/Map';
import { Filters } from './components/Filters';
import { StatsPanel } from './components/StatsPanel';
import { BestDeals } from './components/BestDeals';
import { ActiveListingsPanel } from './components/ActiveListingsPanel';
import { api } from './api/client';
import type { PropertyWithPrediction, ActiveListing, PropertyStats, Filters as FilterType } from './api/client';
import { Home } from 'lucide-react';

type ViewMode = 'sold' | 'active';

function App() {
  const [properties, setProperties] = useState<PropertyWithPrediction[]>([]);
  const [activeListings, setActiveListings] = useState<ActiveListing[]>([]);
  const [deals, setDeals] = useState<PropertyWithPrediction[]>([]);
  const [stats, setStats] = useState<PropertyStats | null>(null);
  const [filters, setFilters] = useState<FilterType>({});
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewMode>('sold');

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

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Home className="text-accent w-6 h-6" />
            <h1 className="text-xl font-bold text-gray-900">Malmö Homes</h1>
          </div>

          {/* View toggle */}
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setView('sold')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                view === 'sold'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Sold ({properties.length})
            </button>
            <button
              onClick={() => setView('active')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                view === 'active'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              For Sale ({activeListings.length})
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            {view === 'sold' ? 'Market Overview' : 'Active Listings'}
          </h2>
          <p className="text-gray-600">
            {view === 'sold'
              ? 'Explore property sales in Malmö with ML-powered price predictions.'
              : 'Current listings for sale — see how asking prices compare to ML predictions.'}
          </p>
        </div>

        <StatsPanel stats={stats} />

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <div className="lg:col-span-1">
            <Filters filters={filters} onChange={setFilters} />
            {view === 'sold' ? (
              <BestDeals deals={deals} loading={loading} />
            ) : (
              <ActiveListingsPanel listings={activeListings} loading={loading} />
            )}
          </div>

          <div className="lg:col-span-3">
            {loading ? (
              <div className="h-[600px] bg-gray-100 rounded-xl animate-pulse flex items-center justify-center text-gray-400">
                Loading map data...
              </div>
            ) : (
              <Map
                properties={properties}
                activeListings={activeListings}
                view={view}
              />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
