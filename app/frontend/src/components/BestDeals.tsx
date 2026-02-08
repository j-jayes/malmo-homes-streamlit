import type { PropertyWithPrediction } from '../api/client';

interface BestDealsProps {
    deals: PropertyWithPrediction[];
    loading: boolean;
}

function formatSEK(val: number | undefined): string {
    if (val === undefined || val === null) return '—';
    return val.toLocaleString('sv-SE') + ' kr';
}

export function BestDeals({ deals, loading }: BestDealsProps) {
    if (loading) {
        return (
            <div className="mt-6 bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl p-6 text-white shadow-lg">
                <h3 className="font-bold text-lg mb-2">🔥 Best Deals</h3>
                <div className="space-y-3">
                    {[...Array(3)].map((_, i) => (
                        <div key={i} className="h-16 bg-gray-700 rounded-lg animate-pulse" />
                    ))}
                </div>
            </div>
        );
    }

    if (!deals.length) return null;

    return (
        <div className="mt-6 bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl p-6 text-white shadow-lg">
            <h3 className="font-bold text-lg mb-1">🔥 Best Deals</h3>
            <p className="text-gray-400 text-xs mb-4">
                Recent properties that sold well below predicted value
            </p>

            <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
                {deals.map((deal) => (
                    <a
                        key={deal.property_id}
                        href={deal.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block bg-gray-800/60 hover:bg-gray-700/60 rounded-lg p-3 transition-colors"
                    >
                        <div className="flex justify-between items-start">
                            <div className="min-w-0 flex-1">
                                <p className="text-sm font-medium truncate">
                                    {deal.address}
                                </p>
                                <p className="text-xs text-gray-400">
                                    {deal.rooms} rum · {deal.area} m²
                                    {deal.neighborhood ? ` · ${deal.neighborhood}` : ''}
                                </p>
                            </div>
                            <span className="ml-2 shrink-0 text-sm font-bold text-green-400">
                                {deal.price_diff_pct}%
                            </span>
                        </div>
                        <div className="mt-2 flex gap-4 text-xs">
                            <span className="text-gray-400">
                                Sold: <span className="text-white font-medium">{formatSEK(deal.price)}</span>
                            </span>
                            <span className="text-gray-400">
                                Pred: <span className="text-gray-300">{formatSEK(deal.predicted_price)}</span>
                            </span>
                        </div>
                    </a>
                ))}
            </div>

            <div className="mt-3 pt-3 border-t border-gray-700">
                <div className="flex items-center gap-2 text-xs text-gray-500">
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    <span>Green = sold below prediction (deal)</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                    <div className="w-2 h-2 rounded-full bg-red-500" />
                    <span>Red = sold above prediction</span>
                </div>
            </div>
        </div>
    );
}
