import { useEffect, useState, useRef } from 'react';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    AreaChart, Area, CartesianGrid, ScatterChart, Scatter,
    Legend, Cell,
} from 'recharts';
import { api } from '../api/client';
import type {
    NeighborhoodStat, RoomStat, PriceTrendPoint,
    BuildingDecadeStat, FeeAnalysisPoint,
} from '../api/client';

interface InsightsPanelProps {
    anchor: string | null;
    onAnchorConsumed: () => void;
}

function formatSEK(val: number | undefined | null): string {
    if (val === undefined || val === null) return '—';
    const abs = Math.abs(val);
    if (abs >= 1_000_000) {
        return (val < 0 ? '-' : '') + (abs / 1_000_000).toFixed(2).replace(/\.?0+$/, '') + ' M kr';
    }
    return Math.round(val).toLocaleString('sv-SE') + ' kr';
}

function formatSqm(val: number): string {
    return Math.round(val).toLocaleString('sv-SE') + ' kr/m²';
}

const CARD = 'bg-white rounded-xl border border-slate-100 shadow-card p-5';
const SECTION_LABEL = 'text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1';
const CHART_TITLE = 'text-sm font-semibold text-slate-800 mb-0.5';
const CHART_SUB = 'text-xs text-slate-400 mb-4';

// ── Tooltip formatters ───────────────────────────────────────────────────────

function SqmTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-white border border-slate-100 rounded-lg shadow-card-hover px-3 py-2 text-xs">
            <p className="font-semibold text-slate-800 mb-1">{label}</p>
            {payload.map((p: any) => (
                <p key={p.dataKey} style={{ color: p.color }}>
                    {p.name}: {formatSqm(p.value)}
                </p>
            ))}
        </div>
    );
}

function PriceTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-white border border-slate-100 rounded-lg shadow-card-hover px-3 py-2 text-xs">
            <p className="font-semibold text-slate-800 mb-1">{label}</p>
            {payload.map((p: any) => (
                <p key={p.dataKey} style={{ color: p.color }}>
                    {p.name}: {formatSEK(p.value)}
                </p>
            ))}
        </div>
    );
}

function DomTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-white border border-slate-100 rounded-lg shadow-card-hover px-3 py-2 text-xs">
            <p className="font-semibold text-slate-800 mb-1">{label}</p>
            {payload.map((p: any) => (
                <p key={p.dataKey} style={{ color: p.color }}>
                    {p.name}: {p.value != null ? Math.round(p.value) + ' days' : '—'}
                </p>
            ))}
        </div>
    );
}

// ── Variable dictionary card ──────────────────────────────────────────────────

interface VarCardProps {
    id: string;
    name: string;
    swedish: string;
    explanation: string;
    range?: string;
}

function VarCard({ id, name, swedish, explanation, range }: VarCardProps) {
    return (
        <div id={id} className={`${CARD} scroll-mt-6`}>
            <p className={SECTION_LABEL}>Variable</p>
            <p className="text-sm font-bold text-slate-900">{name}</p>
            <p className="text-xs text-slate-400 italic mb-2">{swedish}</p>
            <p className="text-xs text-slate-600 leading-relaxed">{explanation}</p>
            {range && (
                <p className="text-[10px] text-slate-400 mt-2 font-medium">
                    Typical Malmö range: <span className="text-slate-500">{range}</span>
                </p>
            )}
        </div>
    );
}

// ── Main component ────────────────────────────────────────────────────────────

export function InsightsPanel({ anchor, onAnchorConsumed }: InsightsPanelProps) {
    const [neighborhoods, setNeighborhoods] = useState<NeighborhoodStat[]>([]);
    const [rooms, setRooms] = useState<RoomStat[]>([]);
    const [trend, setTrend] = useState<PriceTrendPoint[]>([]);
    const [decades, setDecades] = useState<BuildingDecadeStat[]>([]);
    const [feeData, setFeeData] = useState<FeeAnalysisPoint[]>([]);
    const [loading, setLoading] = useState(true);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        Promise.all([
            api.getNeighborhoodStats(),
            api.getRoomStats(),
            api.getPriceTrend(),
            api.getBuildingDecadeStats(),
            api.getFeeAnalysis(),
        ]).then(([n, r, t, d, f]) => {
            setNeighborhoods(n);
            setRooms(r);
            setTrend(t);
            setDecades(d);
            setFeeData(f);
        }).catch(console.error).finally(() => setLoading(false));
    }, []);

    // Scroll to anchor after data loads
    useEffect(() => {
        if (!anchor || loading) return;
        const el = document.getElementById(anchor);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            onAnchorConsumed();
        }
    }, [anchor, loading, onAnchorConsumed]);

    // Show top 20 neighbourhoods for the chart (sorted desc by price/sqm)
    const topNeighborhoods = neighborhoods.slice(0, 20);

    // Separate fee data by area group
    const feeSmall = feeData.filter(d => d.area_group === 'Small (<60m²)');
    const feeLarge = feeData.filter(d => d.area_group === 'Large (≥80m²)');

    // Combine for scatter (recharts ScatterChart with named series)
    const feeScatterSmall = feeSmall.map(d => ({ x: d.fee_bucket, y: d.price, count: d.count }));
    const feeScatterLarge = feeLarge.map(d => ({ x: d.fee_bucket, y: d.price, count: d.count }));

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center bg-canvas">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-8 h-8 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
                    <span className="text-xs text-slate-400">Loading market data…</span>
                </div>
            </div>
        );
    }

    return (
        <div ref={scrollRef} className="flex-1 overflow-y-auto sidebar-scroll bg-canvas">
            <div className="max-w-6xl mx-auto px-6 py-8 space-y-10">

                {/* ── Section A: Market Intelligence ───────────────────── */}
                <div>
                    <h2 className="text-base font-bold text-slate-900 mb-1">Market Intelligence</h2>
                    <p className="text-xs text-slate-400 mb-6">
                        Aggregate patterns across {neighborhoods.reduce((s, n) => s + n.count, 0).toLocaleString('sv-SE')} sold properties in Malmö.
                    </p>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                        {/* 1. Neighbourhood ranking — full width */}
                        <div className={`${CARD} lg:col-span-2`}>
                            <p className={CHART_TITLE}>Neighbourhood Price Ranking</p>
                            <p className={CHART_SUB}>
                                Median price per m² — top 20 neighbourhoods (min. 10 sales). The spread from bottom to top is roughly 4×.
                            </p>
                            <ResponsiveContainer width="100%" height={420}>
                                <BarChart
                                    data={[...topNeighborhoods].reverse()}
                                    layout="vertical"
                                    margin={{ top: 0, right: 80, left: 120, bottom: 0 }}
                                >
                                    <CartesianGrid horizontal={false} stroke="#f1f5f9" />
                                    <XAxis
                                        type="number"
                                        tickFormatter={v => Math.round(v / 1000) + 'k'}
                                        tick={{ fontSize: 10, fill: '#94a3b8' }}
                                        axisLine={false}
                                        tickLine={false}
                                    />
                                    <YAxis
                                        type="category"
                                        dataKey="neighborhood"
                                        width={115}
                                        tick={{ fontSize: 10, fill: '#64748b' }}
                                        axisLine={false}
                                        tickLine={false}
                                    />
                                    <Tooltip content={<SqmTooltip />} />
                                    <Bar
                                        dataKey="median_price_per_sqm"
                                        name="Median kr/m²"
                                        radius={[0, 4, 4, 0]}
                                        maxBarSize={14}
                                    >
                                        {[...topNeighborhoods].reverse().map((_, i) => (
                                            <Cell
                                                key={i}
                                                fill={`hsl(${220 - i * 8}, 80%, ${45 + i * 1.5}%)`}
                                            />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>

                        {/* 2. Days on market by neighbourhood */}
                        <div className={CARD}>
                            <p className={CHART_TITLE}>Days on Market by Neighbourhood</p>
                            <p className={CHART_SUB}>
                                Median days from listing to sold — same top 20. Shorter = higher demand.
                            </p>
                            <ResponsiveContainer width="100%" height={380}>
                                <BarChart
                                    data={[...topNeighborhoods].reverse()}
                                    layout="vertical"
                                    margin={{ top: 0, right: 40, left: 120, bottom: 0 }}
                                >
                                    <CartesianGrid horizontal={false} stroke="#f1f5f9" />
                                    <XAxis
                                        type="number"
                                        tick={{ fontSize: 10, fill: '#94a3b8' }}
                                        axisLine={false}
                                        tickLine={false}
                                        unit=" d"
                                    />
                                    <YAxis
                                        type="category"
                                        dataKey="neighborhood"
                                        width={115}
                                        tick={{ fontSize: 10, fill: '#64748b' }}
                                        axisLine={false}
                                        tickLine={false}
                                    />
                                    <Tooltip content={<DomTooltip />} />
                                    <Bar
                                        dataKey="avg_days_on_market"
                                        name="Median days"
                                        fill="#64748b"
                                        radius={[0, 4, 4, 0]}
                                        maxBarSize={14}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>

                        {/* 3. Rooms */}
                        <div className={CARD}>
                            <p className={CHART_TITLE}>Median Price by Room Count</p>
                            <p className={CHART_SUB}>
                                1–6 rooms. Note: 3+ room jump partly reflects apartment vs. villa mix in the data — treat upper values as indicative.
                            </p>
                            <ResponsiveContainer width="100%" height={240}>
                                <BarChart data={rooms} margin={{ top: 4, right: 16, left: 16, bottom: 4 }}>
                                    <CartesianGrid vertical={false} stroke="#f1f5f9" />
                                    <XAxis
                                        dataKey="rooms"
                                        tickFormatter={v => v + ' rum'}
                                        tick={{ fontSize: 10, fill: '#94a3b8' }}
                                        axisLine={false}
                                        tickLine={false}
                                    />
                                    <YAxis
                                        tickFormatter={v => (v / 1_000_000).toFixed(1) + 'M'}
                                        tick={{ fontSize: 10, fill: '#94a3b8' }}
                                        axisLine={false}
                                        tickLine={false}
                                        width={42}
                                    />
                                    <Tooltip content={<PriceTooltip />} />
                                    <Bar dataKey="median_price" name="Median price" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>

                        {/* 4. Price trend — full width */}
                        <div className={`${CARD} lg:col-span-2`}>
                            <p className={CHART_TITLE}>Price Trend — Last 24 Months</p>
                            <p className={CHART_SUB}>
                                Monthly median sale price. Market peaked in 2022 following rate rises, then recovered. Recent months show stabilisation.
                            </p>
                            <ResponsiveContainer width="100%" height={220}>
                                <AreaChart data={trend} margin={{ top: 4, right: 16, left: 16, bottom: 4 }}>
                                    <defs>
                                        <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid vertical={false} stroke="#f1f5f9" />
                                    <XAxis
                                        dataKey="month"
                                        tick={{ fontSize: 10, fill: '#94a3b8' }}
                                        axisLine={false}
                                        tickLine={false}
                                        interval="preserveStartEnd"
                                    />
                                    <YAxis
                                        tickFormatter={v => (v / 1_000_000).toFixed(1) + 'M'}
                                        tick={{ fontSize: 10, fill: '#94a3b8' }}
                                        axisLine={false}
                                        tickLine={false}
                                        width={42}
                                    />
                                    <Tooltip content={<PriceTooltip />} />
                                    <Area
                                        type="monotone"
                                        dataKey="median_price"
                                        name="Median price"
                                        stroke="#3b82f6"
                                        strokeWidth={2}
                                        fill="url(#trendGrad)"
                                        dot={false}
                                        activeDot={{ r: 4, fill: '#3b82f6' }}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>

                        {/* 5. Building decade */}
                        <div className={CARD}>
                            <p className={CHART_TITLE}>Price/m² by Building Decade</p>
                            <p className={CHART_SUB}>
                                1980s "miljonprogrammet" buildings are the most affordable. 2010s–2020s new builds command the highest price per m².
                            </p>
                            <ResponsiveContainer width="100%" height={240}>
                                <BarChart data={decades} margin={{ top: 4, right: 16, left: 16, bottom: 4 }}>
                                    <CartesianGrid vertical={false} stroke="#f1f5f9" />
                                    <XAxis
                                        dataKey="decade"
                                        tick={{ fontSize: 10, fill: '#94a3b8' }}
                                        axisLine={false}
                                        tickLine={false}
                                    />
                                    <YAxis
                                        tickFormatter={v => Math.round(v / 1000) + 'k'}
                                        tick={{ fontSize: 10, fill: '#94a3b8' }}
                                        axisLine={false}
                                        tickLine={false}
                                        width={36}
                                    />
                                    <Tooltip content={<SqmTooltip />} />
                                    <Bar dataKey="median_price_per_sqm" name="Median kr/m²" fill="#8b5cf6" radius={[4, 4, 0, 0]}>
                                        {decades.map((d, i) => {
                                            const start = d.decade_start;
                                            const isMiljonprog = start >= 1960 && start <= 1980;
                                            const isNew = start >= 2010;
                                            return (
                                                <Cell
                                                    key={i}
                                                    fill={isMiljonprog ? '#64748b' : isNew ? '#8b5cf6' : '#a78bfa'}
                                                />
                                            );
                                        })}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                            <p className="text-[10px] text-slate-400 mt-2">
                                <span className="inline-block w-2 h-2 rounded-sm bg-slate-400 mr-1" />1960s–1980s miljonprogrammet
                                <span className="inline-block w-2 h-2 rounded-sm bg-violet-500 ml-3 mr-1" />2010s–2020s new builds
                            </p>
                        </div>

                        {/* 6. Fee × area interaction */}
                        <div className={CARD}>
                            <p className={CHART_TITLE}>Monthly Fee vs Sale Price</p>
                            <p className={CHART_SUB}>
                                Small (&lt;60m²) vs large (≥80m²) apartments. Higher fees reduce prices more for large flats. Note: in central areas, both fees and prices are elevated — the positive trend for small flats partly reflects location effects.
                            </p>
                            <ResponsiveContainer width="100%" height={240}>
                                <ScatterChart margin={{ top: 4, right: 16, left: 16, bottom: 4 }}>
                                    <CartesianGrid stroke="#f1f5f9" />
                                    <XAxis
                                        type="number"
                                        dataKey="x"
                                        name="Monthly fee"
                                        tickFormatter={v => Math.round(v / 1000) + 'k'}
                                        tick={{ fontSize: 10, fill: '#94a3b8' }}
                                        axisLine={false}
                                        tickLine={false}
                                        label={{ value: 'Fee (kr/mån)', position: 'insideBottomRight', offset: -4, fontSize: 10, fill: '#94a3b8' }}
                                    />
                                    <YAxis
                                        type="number"
                                        dataKey="y"
                                        name="Median price"
                                        tickFormatter={v => (v / 1_000_000).toFixed(1) + 'M'}
                                        tick={{ fontSize: 10, fill: '#94a3b8' }}
                                        axisLine={false}
                                        tickLine={false}
                                        width={42}
                                    />
                                    <Tooltip
                                        cursor={{ strokeDasharray: '3 3' }}
                                        content={({ active, payload }) => {
                                            if (!active || !payload?.length) return null;
                                            const d = payload[0].payload;
                                            return (
                                                <div className="bg-white border border-slate-100 rounded-lg shadow-card-hover px-3 py-2 text-xs">
                                                    <p className="font-semibold text-slate-800">Fee: {Math.round(d.x).toLocaleString('sv-SE')} kr/mån</p>
                                                    <p className="text-slate-500">Median: {formatSEK(d.y)}</p>
                                                    <p className="text-slate-400">{d.count} properties</p>
                                                </div>
                                            );
                                        }}
                                    />
                                    <Legend wrapperStyle={{ fontSize: '10px' }} />
                                    <Scatter name="Small (<60m²)" data={feeScatterSmall} fill="#3b82f6" opacity={0.7} />
                                    <Scatter name="Large (≥80m²)" data={feeScatterLarge} fill="#f97316" opacity={0.7} />
                                </ScatterChart>
                            </ResponsiveContainer>
                        </div>

                    </div>
                </div>

                {/* ── Section B: Variable Dictionary ───────────────────── */}
                <div>
                    <h2 className="text-base font-bold text-slate-900 mb-1">Variable Guide</h2>
                    <p className="text-xs text-slate-400 mb-6">
                        What each model feature means in the Swedish property market. Click "Learn more" in a property explanation to jump here.
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <VarCard
                            id="var-neighborhood"
                            name="Neighbourhood"
                            swedish="Område"
                            explanation="Administrative sub-district. Malmö Live and Davidshall rank among the most expensive. Rosengård and Fosie sit at the lower end. Location is consistently the largest single price driver — our data shows a 4× spread from bottom to top."
                        />
                        <VarCard
                            id="var-living_area"
                            name="Floor Area"
                            swedish="Boarea (m²)"
                            explanation="Interior measured area per Swedish standard SS 21054. Includes hallways and storage rooms inside the flat, but excludes basement storage and communal areas."
                            range="25–150 m²"
                        />
                        <VarCard
                            id="var-rooms"
                            name="Rooms"
                            swedish="Antal rum"
                            explanation="The living room counts as one room. '2 rum och kök' means 1 bedroom + 1 living room (similar to a UK 1-bed). Adding rooms increases price, though the relationship is non-linear above 3 rooms due to property type mix."
                            range="1–6 rum"
                        />
                        <VarCard
                            id="var-association_fee"
                            name="Monthly Fee"
                            swedish="Avgift (kr/mån)"
                            explanation="Paid to the housing cooperative (bostadsrättsförening) covering shared building costs — maintenance, often heating and water. A higher fee increases your true monthly cost and typically suppresses the sale price, especially in larger flats."
                            range="1,500–7,000 kr/mån"
                        />
                        <VarCard
                            id="var-building_year"
                            name="Year Built"
                            swedish="Byggår"
                            explanation="Pre-1950 stock tends to have high ceilings and character but can carry renovation risk. The 1960–80 'miljonprogrammet' era was mass-built housing — functional but lowest prices per m². Post-2000 builds are modern with higher fees but command the highest price per m²."
                            range="1900–2024"
                        />
                        <VarCard
                            id="var-location"
                            name="Location"
                            swedish="Läge (koordinater)"
                            explanation="Latitude and longitude capture micro-location effects — proximity to the waterfront, Malmö C station, Pildammsparken, and major transit routes. Even within a neighbourhood, a 500m difference can meaningfully affect price."
                            range="lat 55.55–55.65, lng 13.00–13.10"
                        />
                        <VarCard
                            id="var-housing_type"
                            name="Housing Type"
                            swedish="Bostadstyp"
                            explanation="Lägenhet (apartment), Villa (detached house), or Radhus (townhouse). Apartments dominate Malmö's market — roughly 80% of transactions. Villas trade at very different price points and drivers than apartments."
                        />
                        <VarCard
                            id="var-ownership_type"
                            name="Ownership Type"
                            swedish="Upplåtelseform"
                            explanation="Bostadsrätt means you own a cooperative share — the building is jointly owned with other residents and you pay a monthly fee. Äganderätt is freehold (you own land and building outright). Bostadsrätt dominates the Malmö apartment market."
                        />
                    </div>
                </div>

            </div>
        </div>
    );
}
