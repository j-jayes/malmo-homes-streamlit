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

export interface ShapFeature {
    feature: string;
    display_name: string;
    value: number;
    shap_value: number;
}

export interface WordImpact {
    word: string;
    impact: number;
    coefficient: number;
    tfidf_score: number;
}

export interface ExplanationResponse {
    property_id: string;
    narrative: string;
    predicted_price?: number;
    asking_price?: number;
    price_diff_pct?: number;
    shap_features: ShapFeature[];
    text_premium?: number;
    word_impacts: WordImpact[];
}

export interface Filters {
    min_price?: number;
    max_price?: number;
    min_area?: number;
    max_area?: number;
    rooms?: number;
    neighborhood?: string;
}

export interface NeighborhoodStat {
    neighborhood: string;
    median_price_per_sqm: number;
    median_price: number;
    count: number;
    avg_days_on_market?: number;
}

export interface RoomStat {
    rooms: number;
    median_price: number;
    median_price_per_sqm: number;
    count: number;
    avg_area: number;
}

export interface PriceTrendPoint {
    month: string;
    median_price: number;
    count: number;
}

export interface BuildingDecadeStat {
    decade: string;
    decade_start: number;
    median_price_per_sqm: number;
    count: number;
}

export interface FeeAnalysisPoint {
    fee_bucket: number;
    price: number;
    area_group: string;
    count: number;
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

    getExplanation: async (propertyId: string): Promise<ExplanationResponse> => {
        const response = await axios.get<ExplanationResponse>(
            `${API_URL}/active/${propertyId}/explanation`
        );
        return response.data;
    },

    getNeighborhoodStats: async (): Promise<NeighborhoodStat[]> => {
        const response = await axios.get<NeighborhoodStat[]>(`${API_URL}/insights/neighborhoods`);
        return response.data;
    },

    getRoomStats: async (): Promise<RoomStat[]> => {
        const response = await axios.get<RoomStat[]>(`${API_URL}/insights/rooms`);
        return response.data;
    },

    getPriceTrend: async (): Promise<PriceTrendPoint[]> => {
        const response = await axios.get<PriceTrendPoint[]>(`${API_URL}/insights/price-trend`);
        return response.data;
    },

    getBuildingDecadeStats: async (): Promise<BuildingDecadeStat[]> => {
        const response = await axios.get<BuildingDecadeStat[]>(`${API_URL}/insights/building-years`);
        return response.data;
    },

    getFeeAnalysis: async (): Promise<FeeAnalysisPoint[]> => {
        const response = await axios.get<FeeAnalysisPoint[]>(`${API_URL}/insights/fee-analysis`);
        return response.data;
    },
};
