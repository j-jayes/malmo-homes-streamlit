import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import type { Property } from '../api/client';
import L from 'leaflet';

// Fix for default marker icon
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});

L.Marker.prototype.options.icon = DefaultIcon;

interface MapProps {
    properties: Property[];
}

export function Map({ properties }: MapProps) {
    const defaultCenter = [55.604981, 13.003822]; // Malmö center

    return (
        <div className="h-[600px] w-full rounded-xl overflow-hidden shadow-lg border border-gray-200">
            <MapContainer
                center={defaultCenter as [number, number]}
                zoom={13}
                style={{ height: '100%', width: '100%' }}
            >
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {properties.map((prop) => (
                    prop.lat && prop.lng && (
                        <Marker key={prop.property_id} position={[prop.lat, prop.lng]}>
                            <Popup>
                                <div className="p-2">
                                    <h3 className="font-bold text-sm">{prop.address}</h3>
                                    <p className="text-xs text-gray-600">{prop.rooms} rum • {prop.area} m²</p>
                                    <p className="font-semibold text-accent mt-1">
                                        {prop.price?.toLocaleString()} SEK
                                    </p>
                                    <a
                                        href={prop.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs text-blue-500 hover:underline mt-2 block"
                                    >
                                        View Listing
                                    </a>
                                </div>
                            </Popup>
                        </Marker>
                    )
                ))}
            </MapContainer>
        </div>
    );
}
