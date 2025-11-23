import axios from 'axios';

const API_URL = 'http://localhost:8000';

export interface Property {
    property_id: string;
    url: string;
    title?: string;
    address?: string;
    city?: string;
    price?: number;
    rooms?: number;
    area?: number;
    monthly_fee?: number;
    lat?: number;
    lng?: number;
    scraped_at: string;
}

export interface PropertyStats {
    total_properties: number;
    avg_price: number;
    avg_price_per_sqm: number;
}

export interface Filters {
    min_price?: number;
    max_price?: number;
    min_area?: number;
    max_area?: number;
    rooms?: number;
}

export const api = {
    getProperties: async (filters: Filters = {}) => {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined) params.append(key, value.toString());
        });
        const response = await axios.get<Property[]>(`${API_URL}/properties`, { params });
        return response.data;
    },

    getStats: async () => {
        const response = await axios.get<PropertyStats>(`${API_URL}/stats`);
        return response.data;
    }
};
