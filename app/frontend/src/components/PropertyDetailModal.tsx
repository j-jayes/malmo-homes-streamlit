import { useEffect, useState } from 'react';
import { X, ExternalLink, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { ActiveListing, ExplanationResponse, ShapFeature } from '../api/client';
import { api } from '../api/client';

// Feature key → Insights anchor for deep-linking
const INSIGHT_ANCHORS: Record<string, string> = {
    neighborhood: 'var-neighborhood',
    living_area: 'var-living_area',
    rooms: 'var-rooms',
    association_fee: 'var-association_fee',
    building_year: 'var-building_year',
};

interface PropertyDetailModalProps {
    listing: ActiveListing;
    onClose: () => void;
    onOpenInsight?: (anchor: string) => void;
}

function formatSEK(val: number | undefined | null): string {
    if (val === undefined || val === null) return '—';
    const abs = Math.abs(val);
    if (abs >= 1_000_000) {
        const m = abs / 1_000_000;
        return (val < 0 ? '-' : '') + m.toFixed(2).replace(/\.?0+$/, '') + ' M kr';
    }
    return val.toLocaleString('sv-SE') + ' kr';
}

function GapBadge({ pct }: { pct: number | undefined | null }) {
    if (pct === undefined || pct === null) return null;
    const isUnder = pct < -5;
    const isOver = pct > 5;
    const cfg = isUnder
        ? { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: <TrendingDown size={12} /> }
        : isOver
        ? { bg: 'bg-red-50 text-red-600 border-red-200', icon: <TrendingUp size={12} /> }
        : { bg: 'bg-slate-100 text-slate-600 border-slate-200', icon: <Minus size={12} /> };
    const label = isUnder ? 'Below model estimate' : isOver ? 'Above model estimate' : 'Near model estimate';
    return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${cfg.bg}`}>
            {cfg.icon}
            {pct > 0 ? '+' : ''}{pct.toFixed(1)}% · {label}
        </span>
    );
}

function ShapBar({
    feature,
    maxAbs,
    onOpenInsight,
}: {
    feature: ShapFeature;
    maxAbs: number;
    onOpenInsight?: (anchor: string) => void;
}) {
    const isPositive = feature.shap_value >= 0;
    const widthPct = maxAbs > 0 ? Math.min(100, (Math.abs(feature.shap_value) / maxAbs) * 100) : 0;
    const anchor = INSIGHT_ANCHORS[feature.feature];

    return (
        <div className="py-0.5">
            <div className="flex items-center gap-2">
                <span className="w-32 text-[11px] text-slate-500 truncate shrink-0 text-right" title={feature.display_name}>
                    {feature.display_name}
                </span>
                <div className="flex-1 relative h-5 flex items-center">
                    {/* Centre line */}
                    <div className="absolute left-1/2 top-0 bottom-0 w-px bg-slate-200" />
                    {isPositive ? (
                        <div
                            className="absolute left-1/2 h-3 rounded-r-sm bg-emerald-500/80"
                            style={{ width: `${widthPct / 2}%` }}
                        />
                    ) : (
                        <div
                            className="absolute h-3 rounded-l-sm bg-red-400/80"
                            style={{ right: '50%', width: `${widthPct / 2}%` }}
                        />
                    )}
                </div>
                <span className={`w-20 text-[11px] text-right shrink-0 font-medium tabular-nums ${isPositive ? 'text-emerald-700' : 'text-red-600'}`}>
                    {isPositive ? '+' : ''}{formatSEK(feature.shap_value)}
                </span>
            </div>
            {anchor && onOpenInsight && (
                <div className="flex justify-end pr-0 pl-34 mt-0.5">
                    <button
                        onClick={() => onOpenInsight(anchor)}
                        className="text-[10px] text-brand-500 hover:text-brand-700 cursor-pointer pl-36"
                    >
                        Learn more →
                    </button>
                </div>
            )}
        </div>
    );
}

export function PropertyDetailModal({ listing, onClose, onOpenInsight }: PropertyDetailModalProps) {
    const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setLoading(true);
        setError(null);
        api.getExplanation(listing.property_id)
            .then(setExplanation)
            .catch(() => setError('No explanation available for this property yet. Run the pipeline with --explain to generate one.'))
            .finally(() => setLoading(false));
    }, [listing.property_id]);

    const handleBackdrop = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) onClose();
    };

    const topShap = explanation?.shap_features?.slice(0, 7) ?? [];
    const maxAbs = topShap.length > 0 ? Math.max(...topShap.map(f => Math.abs(f.shap_value))) : 1;
    const topWords = (explanation?.word_impacts ?? [])
        .filter(w => Math.abs(w.impact) > 5_000)
        .slice(0, 8);

    return (
        <div
            className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-slate-900/40 backdrop-blur-[2px] p-0 sm:p-6"
            onClick={handleBackdrop}
        >
            <div className="relative bg-white rounded-t-2xl sm:rounded-2xl w-full sm:max-w-xl max-h-[94vh] overflow-y-auto sidebar-scroll shadow-2xl ring-1 ring-slate-900/5">

                {/* ─── Header ─── */}
                <div className="sticky top-0 bg-white/95 backdrop-blur-sm border-b border-slate-100 px-5 py-4 flex items-start justify-between z-10">
                    <div>
                        <p className="font-bold text-slate-900 text-base leading-snug">{listing.address}</p>
                        <p className="text-xs text-slate-400 mt-0.5">
                            {[listing.neighborhood, listing.rooms && `${listing.rooms} rum`, listing.area && `${listing.area} m²`]
                                .filter(Boolean).join(' · ')}
                        </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0 ml-3 mt-0.5">
                        <a
                            href={listing.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                            title="Open on Hemnet"
                        >
                            <ExternalLink size={15} />
                        </a>
                        <button
                            onClick={onClose}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                        >
                            <X size={15} />
                        </button>
                    </div>
                </div>

                <div className="px-5 py-5 space-y-6">

                    {/* ─── Price summary card ─── */}
                    <div className="bg-slate-50 rounded-xl p-4 ring-1 ring-slate-100">
                        <div className="grid grid-cols-2 gap-4 mb-3">
                            <div>
                                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Asking price</p>
                                <p className="text-xl font-bold text-slate-900 tabular-nums">{formatSEK(listing.price)}</p>
                            </div>
                            <div>
                                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Model estimate</p>
                                <p className="text-xl font-bold text-blue-600 tabular-nums">
                                    {explanation?.predicted_price ? formatSEK(explanation.predicted_price) : loading ? '…' : '—'}
                                </p>
                            </div>
                        </div>
                        {explanation && <GapBadge pct={explanation.price_diff_pct} />}
                    </div>

                    {/* ─── Loading skeleton ─── */}
                    {loading && (
                        <div className="space-y-2.5">
                            {[90, 75, 80, 60].map((w, i) => (
                                <div key={i} className="h-3.5 bg-slate-100 rounded-full animate-pulse" style={{ width: `${w}%` }} />
                            ))}
                        </div>
                    )}

                    {/* ─── Error ─── */}
                    {!loading && error && (
                        <div className="bg-slate-50 rounded-xl p-4 text-xs text-slate-500 border border-slate-100 italic">
                            {error}
                        </div>
                    )}

                    {/* ─── Narrative ─── */}
                    {!loading && explanation?.narrative && (
                        <div>
                            <h3 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2.5">Analysis</h3>
                            <div className="text-sm text-slate-700 leading-relaxed space-y-2.5">
                                {explanation.narrative.split('\n\n').map((para, i) => (
                                    <p key={i}>{para}</p>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* ─── SHAP waterfall ─── */}
                    {!loading && topShap.length > 0 && (
                        <div>
                            <h3 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Price drivers</h3>
                            <p className="text-[11px] text-slate-400 mb-3">Each feature's contribution relative to the market average</p>
                            <div className="space-y-0">
                                {topShap.map(f => (
                                    <ShapBar
                                        key={f.feature}
                                        feature={f}
                                        maxAbs={maxAbs}
                                        onOpenInsight={onOpenInsight}
                                    />
                                ))}
                            </div>
                            <div className="flex justify-between text-[10px] text-slate-400 mt-1.5 pl-36 pr-20 px-2">
                                <span>— reduces</span>
                                <span>adds +</span>
                            </div>
                        </div>
                    )}

                    {/* ─── Word impacts ─── */}
                    {!loading && topWords.length > 0 && (
                        <div>
                            <h3 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Description signals</h3>
                            {explanation?.text_premium != null && (
                                <p className="text-[11px] text-slate-400 mb-2.5">
                                    Ad text contributes{' '}
                                    <span className={`font-semibold ${explanation.text_premium >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                                        {explanation.text_premium >= 0 ? '+' : ''}{formatSEK(explanation.text_premium)}
                                    </span>{' '}
                                    to the estimated value.
                                </p>
                            )}
                            <div className="flex flex-wrap gap-1.5">
                                {topWords.map(w => (
                                    <span
                                        key={w.word}
                                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium border ${
                                            w.impact >= 0
                                                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                                                : 'bg-red-50 text-red-700 border-red-200'
                                        }`}
                                    >
                                        {w.word}
                                        <span className="opacity-60 tabular-nums">
                                            {w.impact >= 0 ? '+' : ''}{formatSEK(w.impact)}
                                        </span>
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
