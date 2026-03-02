import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import type { PropertyWithPrediction, ActiveListing } from '../api/client';

interface MapProps {
    properties: PropertyWithPrediction[];
    activeListings?: ActiveListing[];
    view: 'sold' | 'active';
}

function getDealColor(pct: number | undefined): string {
    if (pct === undefined || pct === null) return '#6b7280'; // gray
    if (pct <= -20) return '#15803d'; // deep green — great deal
    if (pct <= -10) return '#22c55e'; // green — good deal
    if (pct <= -5) return '#86efac';  // light green
    if (pct <= 5) return '#6b7280';   // gray — fair price
    if (pct <= 10) return '#fbbf24';  // amber
    if (pct <= 20) return '#f97316';  // orange
    return '#dc2626';                 // red — overpaid
}

function formatSEK(val: number | undefined): string {
    if (val === undefined || val === null) return '—';
    return val.toLocaleString('sv-SE') + ' kr';
}

function getActiveColor(pct: number | undefined): string {
    if (pct === undefined || pct === null) return '#3b82f6'; // blue
    if (pct <= -15) return '#15803d'; // deep green — great deal
    if (pct <= -5) return '#22c55e';  // green — good deal
    if (pct <= 5) return '#3b82f6';   // blue — fair price
    if (pct <= 15) return '#f97316';  // orange — somewhat overpriced
    return '#dc2626';                 // red — overpriced
}

export function Map({ properties, activeListings = [], view }: MapProps) {
    const defaultCenter: [number, number] = [55.604981, 13.003822];

    return (
        <div className="absolute inset-0 overflow-hidden">
            <MapContainer
                center={defaultCenter}
                zoom={13}
                style={{ height: '100%', width: '100%' }}
            >
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />

                {/* Sold properties — shown when view is 'sold' */}
                {view === 'sold' && properties.map(
                    (prop) =>
                        prop.lat &&
                        prop.lng && (
                            <CircleMarker
                                key={prop.property_id}
                                center={[prop.lat, prop.lng]}
                                radius={6}
                                pathOptions={{
                                    fillColor: getDealColor(prop.price_diff_pct),
                                    color: '#fff',
                                    weight: 1.5,
                                    fillOpacity: 0.85,
                                }}
                            >
                                <Popup>
                                    <div className="min-w-[210px] p-3">
                                        <h3 className="font-bold text-sm mb-1">{prop.address}</h3>
                                        {prop.neighborhood && (
                                            <p className="text-xs text-gray-500 mb-2">{prop.neighborhood}</p>
                                        )}
                                        <p className="text-xs text-gray-600">
                                            {prop.rooms} rum · {prop.area} m²
                                            {prop.monthly_fee ? ` · ${prop.monthly_fee?.toLocaleString('sv-SE')} kr/mån` : ''}
                                        </p>

                                        <div className="mt-2 pt-2 border-t border-gray-200 space-y-1">
                                            <div className="flex justify-between text-xs">
                                                <span className="text-gray-500">Sold for</span>
                                                <span className="font-semibold">{formatSEK(prop.price)}</span>
                                            </div>
                                            {prop.predicted_price && (
                                                <div className="flex justify-between text-xs">
                                                    <span className="text-gray-500">Predicted</span>
                                                    <span className="font-medium text-gray-700">
                                                        {formatSEK(prop.predicted_price)}
                                                    </span>
                                                </div>
                                            )}
                                            {prop.price_diff_pct !== undefined && prop.price_diff_pct !== null && (
                                                <div className="flex justify-between text-xs">
                                                    <span className="text-gray-500">Difference</span>
                                                    <span
                                                        className={`font-bold ${
                                                            prop.price_diff_pct < -5
                                                                ? 'text-green-600'
                                                                : prop.price_diff_pct > 5
                                                                ? 'text-red-500'
                                                                : 'text-gray-600'
                                                        }`}
                                                    >
                                                        {prop.price_diff_pct > 0 ? '+' : ''}
                                                        {prop.price_diff_pct}%
                                                    </span>
                                                </div>
                                            )}
                                        </div>

                                        {prop.sold_date && (
                                            <p className="text-xs text-gray-400 mt-2">Sold {prop.sold_date}</p>
                                        )}
                                        <a
                                            href={prop.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-xs text-blue-600 hover:text-blue-800 hover:underline mt-2 block font-medium"
                                        >
                                            View on Hemnet →
                                        </a>
                                    </div>
                                </Popup>
                            </CircleMarker>
                        )
                )}

                {/* Active listings — shown when view is 'active' */}
                {view === 'active' && activeListings.map(
                    (listing) =>
                        listing.lat &&
                        listing.lng && (
                            <CircleMarker
                                key={listing.property_id}
                                center={[listing.lat, listing.lng]}
                                radius={7}
                                pathOptions={{
                                    fillColor: getActiveColor(listing.price_diff_pct),
                                    color: '#1e40af',
                                    weight: 2,
                                    fillOpacity: 0.9,
                                }}
                            >
                                <Popup>
                                    <div className="min-w-[210px] p-3">
                                        <div className="flex items-center gap-1 mb-1">
                                            <span className="bg-blue-50 text-blue-700 text-[10px] font-semibold px-2 py-0.5 rounded-full border border-blue-100">For Sale</span>
                                        </div>
                                        <h3 className="font-bold text-sm mb-1">{listing.address}</h3>
                                        {listing.neighborhood && (
                                            <p className="text-xs text-gray-500 mb-2">{listing.neighborhood}</p>
                                        )}
                                        <p className="text-xs text-gray-600">
                                            {listing.rooms} rum · {listing.area} m²
                                            {listing.monthly_fee ? ` · ${listing.monthly_fee?.toLocaleString('sv-SE')} kr/mån` : ''}
                                        </p>

                                        <div className="mt-2 pt-2 border-t border-gray-200 space-y-1">
                                            <div className="flex justify-between text-xs">
                                                <span className="text-gray-500">Asking price</span>
                                                <span className="font-semibold">{formatSEK(listing.price)}</span>
                                            </div>
                                            {listing.predicted_price && (
                                                <div className="flex justify-between text-xs">
                                                    <span className="text-gray-500">ML Predicted</span>
                                                    <span className="font-medium text-gray-700">
                                                        {formatSEK(listing.predicted_price)}
                                                    </span>
                                                </div>
                                            )}
                                            {listing.price_diff_pct !== undefined && listing.price_diff_pct !== null && (
                                                <div className="flex justify-between text-xs">
                                                    <span className="text-gray-500">vs Prediction</span>
                                                    <span
                                                        className={`font-bold ${
                                                            listing.price_diff_pct < -5
                                                                ? 'text-green-600'
                                                                : listing.price_diff_pct > 5
                                                                ? 'text-red-500'
                                                                : 'text-gray-600'
                                                        }`}
                                                    >
                                                        {listing.price_diff_pct > 0 ? '+' : ''}
                                                        {listing.price_diff_pct}%
                                                    </span>
                                                </div>
                                            )}
                                        </div>

                                        {listing.days_on_market !== undefined && listing.days_on_market !== null && (
                                            <p className="text-xs text-gray-400 mt-2">
                                                {listing.days_on_market} days on market
                                            </p>
                                        )}
                                        <a
                                            href={listing.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-xs text-blue-600 hover:text-blue-800 hover:underline mt-2 block font-medium"
                                        >
                                            View on Hemnet →
                                        </a>
                                    </div>
                                </Popup>
                            </CircleMarker>
                        )
                )}
            </MapContainer>
        </div>
    );
}
