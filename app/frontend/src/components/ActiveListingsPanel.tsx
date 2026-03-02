import type { ActiveListing } from '../api/client';
import { Sparkles } from 'lucide-react';

interface ActiveListingsPanelProps {
    listings: ActiveListing[];
    loading: boolean;
    onSelect?: (listing: ActiveListing) => void;
}

function formatSEK(val: number | undefined): string {
    if (val === undefined || val === null) return '—';
    if (val >= 1_000_000) return (val / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
    return Math.round(val / 1_000) + 'k';
}

function gapStyle(pct: number | undefined | null) {
    if (pct === undefined || pct === null) return { bar: 'bg-slate-200', badge: '', label: '' };
    if (pct < -15) return { bar: 'bg-emerald-600', badge: 'bg-emerald-50 text-emerald-700 border border-emerald-200', label: '' };
    if (pct < -5)  return { bar: 'bg-emerald-400', badge: 'bg-green-50 text-green-700 border border-green-200',     label: '' };
    if (pct <= 5)  return { bar: 'bg-slate-300',   badge: 'bg-slate-100 text-slate-500',                            label: '' };
    if (pct <= 15) return { bar: 'bg-amber-400',   badge: 'bg-amber-50 text-amber-700 border border-amber-200',     label: '' };
    return              { bar: 'bg-red-400',     badge: 'bg-red-50 text-red-600 border border-red-200',           label: '' };
}

export function ActiveListingsPanel({ listings, loading, onSelect }: ActiveListingsPanelProps) {
    if (loading) {
        return (
            <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-[84px] bg-slate-100 rounded-xl animate-pulse" />
                ))}
            </div>
        );
    }

    if (!listings.length) {
        return (
            <p className="text-xs text-slate-400 py-4 text-center">
                No active listings available yet.
            </p>
        );
    }

    return (
        <div className="space-y-1.5">
            {listings.map((listing) => {
                const { bar, badge } = gapStyle(listing.price_diff_pct);
                return (
                    <div
                        key={listing.property_id}
                        role="button"
                        tabIndex={0}
                        onClick={() => onSelect?.(listing)}
                        onKeyDown={(e) => e.key === 'Enter' && onSelect?.(listing)}
                        className={`
                            group bg-white border border-slate-100 rounded-xl p-3
                            hover:border-slate-200 hover:shadow-card-hover
                            transition-all duration-150 cursor-pointer
                            border-l-4 ${bar}
                        `}
                    >
                        <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0 flex-1">
                                <p className="text-sm font-semibold text-slate-900 truncate leading-tight">
                                    {listing.address}
                                </p>
                                <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                                    {[listing.neighborhood, listing.rooms && `${listing.rooms} rum`, listing.area && `${listing.area} m²`]
                                        .filter(Boolean).join(' · ')}
                                </p>
                            </div>
                            {listing.price_diff_pct !== undefined && listing.price_diff_pct !== null && (
                                <span className={`shrink-0 text-[11px] font-bold px-1.5 py-0.5 rounded-md ${badge}`}>
                                    {listing.price_diff_pct > 0 ? '+' : ''}{listing.price_diff_pct}%
                                </span>
                            )}
                        </div>
                        <div className="mt-2 flex items-center justify-between text-[11px]">
                            <span className="font-semibold text-slate-800">{formatSEK(listing.price)} kr</span>
                            <div className="flex items-center gap-2 text-slate-400">
                                {listing.predicted_price && (
                                    <span>pred <span className="text-slate-500">{formatSEK(listing.predicted_price)} kr</span></span>
                                )}
                                {listing.days_on_market != null && (
                                    <span>{listing.days_on_market}d</span>
                                )}
                            </div>
                        </div>
                        {onSelect && (
                            <div className="mt-1.5 flex items-center gap-1 text-[10px] text-brand-500 opacity-0 group-hover:opacity-100 transition-opacity">
                                <Sparkles size={9} />
                                <span>Click for AI explanation</span>
                            </div>
                        )}
                    </div>
                );
            })}

            <div className="pt-2 flex items-center gap-3 text-[10px] text-slate-400">
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-sm bg-emerald-400 inline-block" /> asking below estimate
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-sm bg-red-400 inline-block" /> asking above estimate
                </span>
            </div>
        </div>
    );
}
