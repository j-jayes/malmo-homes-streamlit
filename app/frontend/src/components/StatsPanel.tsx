import type { PropertyStats } from '../api/client';
// import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface StatsPanelProps {
    stats: PropertyStats | null;
}

export function StatsPanel({ stats }: StatsPanelProps) {
    if (!stats) return null;

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <p className="text-sm text-gray-500">Total Properties</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total_properties}</p>
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
        </div>
    );
}
