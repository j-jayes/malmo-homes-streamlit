import type { PropertyStats } from '../api/client';

interface StatsPanelProps {
    stats: PropertyStats | null;
}

export function StatsPanel({ stats }: StatsPanelProps) {
    if (!stats) return null;

    return (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <p className="text-sm text-gray-500">Sold Properties</p>
                <p className="text-2xl font-bold text-gray-900">
                    {stats.total_properties.toLocaleString()}
                </p>
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <p className="text-sm text-gray-500">Active Listings</p>
                <p className="text-2xl font-bold text-blue-600">
                    {stats.active_listings_count?.toLocaleString() ?? '—'}
                </p>
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <p className="text-sm text-gray-500">Average Price</p>
                <p className="text-2xl font-bold text-gray-900">
                    {stats.avg_price?.toLocaleString(undefined, { maximumFractionDigits: 0 })} SEK
                </p>
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <p className="text-sm text-gray-500">Avg Price / m²</p>
                <p className="text-2xl font-bold text-gray-900">
                    {stats.avg_price_per_sqm?.toLocaleString(undefined, { maximumFractionDigits: 0 })} SEK
                </p>
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <p className="text-sm text-gray-500">ML Predictions</p>
                <p className="text-2xl font-bold text-gray-900">
                    {stats.predictions_count.toLocaleString()}
                </p>
                {stats.model_avg_error_pct !== undefined && stats.model_avg_error_pct !== null && (
                    <p className="text-xs text-gray-400 mt-1">
                        Avg error: ±{stats.model_avg_error_pct}%
                    </p>
                )}
            </div>
        </div>
    );
}
