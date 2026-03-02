import type { PropertyWithPrediction } from '../api/client';

interface BestDealsProps {
    deals: PropertyWithPrediction[];
    loading: boolean;
}

function formatSEK(val: number | undefined): string {
    if (val === undefined || val === null) return '—';
    if (val >= 1_000_000) return (val / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
    return Math.round(val / 1_000) + 'k';
}

function dealColor(pct: number | undefined | null) {
    if (pct === undefined || pct === null) return { bar: 'bg-slate-200', badge: 'bg-slate-100 text-slate-500', text: pct };
    if (pct <= -10) return { bar: 'bg-emerald-500', badge: 'bg-emerald-50 text-emerald-700 border border-emerald-200', text: pct };
    if (pct <= -5)  return { bar: 'bg-green-400',   badge: 'bg-green-50 text-green-700 border border-green-200',   text: pct };
    if (pct >= 10)  return { bar: 'bg-red-400',     badge: 'bg-red-50 text-red-600 border border-red-200',         text: pct };
    if (pct >= 5)   return { bar: 'bg-amber-400',   badge: 'bg-amber-50 text-amber-700 border border-amber-200',   text: pct };
    return               { bar: 'bg-slate-300',   badge: 'bg-slate-100 text-slate-500',                           text: pct };
}

export function BestDeals({ deals, loading }: BestDealsProps) {
    if (loading) {
        return (
            <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-[76px] bg-slate-100 rounded-xl animate-pulse" />
                ))}
            </div>
        );
    }

    if (!deals.length) {
        return (
            <p className="text-xs text-slate-400 py-4 text-center">
                No deal data yet.
            </p>
        );
    }

    return (
        <div className="space-y-1.5">
            {deals.map((deal) => {
                const { bar, badge } = dealColor(deal.price_diff_pct);
                return (
                    <a
                        key={deal.property_id}
                        href={deal.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`
                            group block bg-white border border-slate-100 rounded-xl p-3
                            hover:border-slate-200 hover:shadow-card-hover
                            transition-all duration-150 cursor-pointer
                            border-l-4 ${bar}
                        `}
                    >
                        <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0 flex-1">
                                <p className="text-sm font-semibold text-slate-900 truncate leading-tight">
                                    {deal.address}
                                </p>
                                <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                                    {[deal.neighborhood, deal.rooms && `${deal.rooms} rum`, deal.area && `${deal.area} m²`]
                                        .filter(Boolean).join(' · ')}
                                </p>
                            </div>
                            {deal.price_diff_pct !== undefined && deal.price_diff_pct !== null && (
                                <span className={`shrink-0 text-[11px] font-bold px-1.5 py-0.5 rounded-md ${badge}`}>
                                    {deal.price_diff_pct > 0 ? '+' : ''}{deal.price_diff_pct}%
                                </span>
                            )}
                        </div>
                        <div className="mt-2 flex items-center gap-3 text-[11px]">
                            <span className="font-semibold text-slate-800">{formatSEK(deal.price)} kr</span>
                            {deal.predicted_price && (
                                <span className="text-slate-400">
                                    pred <span className="text-slate-500">{formatSEK(deal.predicted_price)} kr</span>
                                </span>
                            )}
                        </div>
                    </a>
                );
            })}

            <div className="pt-2 flex items-center gap-3 text-[10px] text-slate-400">
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-sm bg-emerald-500 inline-block" /> sold below prediction
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-sm bg-red-400 inline-block" /> sold above prediction
                </span>
            </div>
        </div>
    );
}
