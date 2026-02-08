import { useEffect, useState } from 'react';
import { Map } from './components/Map';
import { Filters } from './components/Filters';
import { StatsPanel } from './components/StatsPanel';
import { BestDeals } from './components/BestDeals';
import { api } from './api/client';
import type { PropertyWithPrediction, PropertyStats, Filters as FilterType } from './api/client';
import { Home } from 'lucide-react';

function App() {
  const [properties, setProperties] = useState<PropertyWithPrediction[]>([]);
  const [deals, setDeals] = useState<PropertyWithPrediction[]>([]);
  const [stats, setStats] = useState<PropertyStats | null>(null);
  const [filters, setFilters] = useState<FilterType>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [propsData, statsData, dealsData] = await Promise.all([
          api.getPropertiesWithPredictions(filters),
          api.getStats(),
          api.getDeals(10),
        ]);
        setProperties(propsData);
        setStats(statsData);
        setDeals(dealsData);
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
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Market Overview</h2>
          <p className="text-gray-600">
            Explore property sales in Malmö with ML-powered price predictions.
          </p>
        </div>

        <StatsPanel stats={stats} />

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <div className="lg:col-span-1">
            <Filters filters={filters} onChange={setFilters} />
            <BestDeals deals={deals} loading={loading} />
          </div>

          <div className="lg:col-span-3">
            {loading ? (
              <div className="h-[600px] bg-gray-100 rounded-xl animate-pulse flex items-center justify-center text-gray-400">
                Loading map data...
              </div>
            ) : (
              <Map properties={properties} />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
