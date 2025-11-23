import { useEffect, useState } from 'react';
import { Map } from './components/Map';
import { Filters } from './components/Filters';
import { StatsPanel } from './components/StatsPanel';
import { api } from './api/client';
import type { Property, PropertyStats, Filters as FilterType } from './api/client';
import { Layout, Home } from 'lucide-react';

function App() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [stats, setStats] = useState<PropertyStats | null>(null);
  const [filters, setFilters] = useState<FilterType>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [propsData, statsData] = await Promise.all([
          api.getProperties(filters),
          api.getStats()
        ]);
        setProperties(propsData);
        setStats(statsData);
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
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Home className="text-accent w-6 h-6" />
            <h1 className="text-xl font-bold text-gray-900">Malmö Homes</h1>
          </div>
          <div className="flex items-center gap-4">
            <button className="p-2 text-gray-500 hover:text-gray-700">
              <Layout className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Market Overview</h2>
          <p className="text-gray-600">Explore historical property sales in Malmö.</p>
        </div>

        <StatsPanel stats={stats} />

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar Filters */}
          <div className="lg:col-span-1">
            <Filters filters={filters} onChange={setFilters} />

            {/* Best Deals Placeholder */}
            <div className="mt-6 bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl p-6 text-white shadow-lg">
              <h3 className="font-bold text-lg mb-2">🔥 Best Deals</h3>
              <p className="text-gray-300 text-sm mb-4">
                AI-powered deal finding coming soon. We'll analyze current listings to find underpriced gems.
              </p>
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div className="h-full bg-accent w-2/3 animate-pulse"></div>
              </div>
              <p className="text-xs text-gray-400 mt-2">Model training in progress...</p>
            </div>
          </div>

          {/* Map Area */}
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
