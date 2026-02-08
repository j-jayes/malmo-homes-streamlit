import type { ActiveListing } from '../api/client';

interface ActiveListingsPanelProps {
    listings: ActiveListing[];
    loading: boolean;
}

function formatSEK(val: number | undefined): string {
    if (val === undefined || val === null) return '—';
    return val.toLocaleString('sv-SE') + ' kr';
}

export function ActiveListingsPanel({ listings, loading }: ActiveListingsPanelProps) {
    if (loading) {
        return (
            <div className="mt-6 bg-gradient-to-br from-blue-900 to-blue-800 rounded-xl p-6 text-white shadow-lg">
                <h3 className="font-bold text-lg mb-2">🏠 For Sale</h3>
                <div className="space-y-3">
                    {[...Array(3)].map((_, i) => (
                        <div key={i} className="h-16 bg-blue-700 rounded-lg animate-pulse" />
                    ))}
                </div>
            </div>
        );
    }

    if (!listings.length) {
        return (
            <div className="mt-6 bg-gradient-to-br from-blue-900 to-blue-800 rounded-xl p-6 text-white shadow-lg">
                <h3 className="font-bold text-lg mb-2">🏠 For Sale</h3>
                <p className="text-blue-300 text-sm">No active listings available yet.</p>
            </div>
        );
    }

    return (
        <div className="mt-6 bg-gradient-to-br from-blue-900 to-blue-800 rounded-xl p-6 text-white shadow-lg">
            <h3 className="font-bold text-lg mb-1">🏠 For Sale Now</h3>
            <p className="text-blue-300 text-xs mb-4">
                {listings.length} active listing{listings.length !== 1 ? 's' : ''} with price predictions
            </p>

            <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
                {listings.map((listing) => (
                    <a
                        key={listing.property_id}
                        href={listing.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block bg-blue-800/60 hover:bg-blue-700/60 rounded-lg p-3 transition-colors"
                    >
                        <div className="flex justify-between items-start">
                            <div className="min-w-0 flex-1">
                                <p className="text-sm font-medium truncate">
                                    {listing.address}
                                </p>
                                <p className="text-xs text-blue-300">
                                    {listing.rooms} rum · {listing.area} m²
                                    {listing.neighborhood ? ` · ${listing.neighborhood}` : ''}
                                </p>
                            </div>
                            {listing.price_diff_pct !== undefined && listing.price_diff_pct !== null && (
                                <span
                                    className={`ml-2 shrink-0 text-sm font-bold ${
                                        listing.price_diff_pct > 5
                                            ? 'text-red-400'
                                            : listing.price_diff_pct < -5
                                            ? 'text-green-400'
                                            : 'text-gray-300'
                                    }`}
                                >
                                    {listing.price_diff_pct > 0 ? '+' : ''}
                                    {listing.price_diff_pct}%
                                </span>
                            )}
                        </div>
                        <div className="mt-2 flex gap-4 text-xs">
                            <span className="text-blue-300">
                                Asking: <span className="text-white font-medium">{formatSEK(listing.price)}</span>
                            </span>
                            {listing.predicted_price && (
                                <span className="text-blue-300">
                                    Pred: <span className="text-blue-100">{formatSEK(listing.predicted_price)}</span>
                                </span>
                            )}
                        </div>
                        {listing.days_on_market !== undefined && listing.days_on_market !== null && (
                            <p className="text-xs text-blue-400 mt-1">
                                {listing.days_on_market} days on market
                            </p>
                        )}
                    </a>
                ))}
            </div>

            <div className="mt-3 pt-3 border-t border-blue-700">
                <div className="flex items-center gap-2 text-xs text-blue-400">
                    <div className="w-2 h-2 rounded-full bg-green-400" />
                    <span>Green % = asking below predicted (potential deal)</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-blue-400 mt-1">
                    <div className="w-2 h-2 rounded-full bg-red-400" />
                    <span>Red % = asking above predicted (overpriced)</span>
                </div>
            </div>
        </div>
    );
}
