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

export interface PropertyWithPrediction {
    property_id: string;
    url: string;
    address?: string;
    city?: string;
    price?: number;
    rooms?: number;
    area?: number;
    monthly_fee?: number;
    lat?: number;
    lng?: number;
    neighborhood?: string;
    sold_date?: string;
    scraped_at?: string;
    predicted_price?: number;
    confidence_low?: number;
    confidence_high?: number;
    predicted_price_per_sqm?: number;
    price_diff?: number;
    price_diff_pct?: number;
}

export interface PropertyStats {
    total_properties: number;
    avg_price: number;
    avg_price_per_sqm: number;
    predictions_count: number;
    model_avg_error_pct?: number;
    active_listings_count: number;
}

export interface ActiveListing {
    property_id: string;
    url: string;
    address?: string;
    city?: string;
    price?: number;
    rooms?: number;
    area?: number;
    monthly_fee?: number;
    lat?: number;
    lng?: number;
    neighborhood?: string;
    listed_date?: string;
    days_on_market?: number;
    scraped_at?: string;
    predicted_price?: number;
    confidence_low?: number;
    confidence_high?: number;
    predicted_price_per_sqm?: number;
    price_diff?: number;
    price_diff_pct?: number;
}

export interface Filters {
    min_price?: number;
    max_price?: number;
    min_area?: number;
    max_area?: number;
    rooms?: number;
    neighborhood?: string;
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

    getPropertiesWithPredictions: async (filters: Filters = {}) => {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined) params.append(key, value.toString());
        });
        const response = await axios.get<PropertyWithPrediction[]>(
            `${API_URL}/properties/predicted`,
            { params }
        );
        return response.data;
    },

    getDeals: async (limit: number = 10) => {
        const response = await axios.get<PropertyWithPrediction[]>(
            `${API_URL}/deals`,
            { params: { limit } }
        );
        return response.data;
    },

    getStats: async () => {
        const response = await axios.get<PropertyStats>(`${API_URL}/stats`);
        return response.data;
    },

    getActiveListings: async (filters: Filters = {}) => {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined) params.append(key, value.toString());
        });
        const response = await axios.get<ActiveListing[]>(
            `${API_URL}/active`,
            { params }
        );
        return response.data;
    },
};
