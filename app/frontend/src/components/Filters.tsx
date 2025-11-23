import type { Filters as FilterType } from '../api/client';

interface FiltersProps {
    filters: FilterType;
    onChange: (filters: FilterType) => void;
}

export function Filters({ filters, onChange }: FiltersProps) {
    const handleChange = (key: keyof FilterType, value: string) => {
        const numValue = value ? Number(value) : undefined;
        onChange({ ...filters, [key]: numValue });
    };

    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 space-y-4">
            <h2 className="font-semibold text-gray-800 mb-4">Filters</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Min Price (SEK)</label>
                    <input
                        type="number"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-accent focus:border-accent"
                        placeholder="0"
                        onChange={(e) => handleChange('min_price', e.target.value)}
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Max Price (SEK)</label>
                    <input
                        type="number"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-accent focus:border-accent"
                        placeholder="10000000"
                        onChange={(e) => handleChange('max_price', e.target.value)}
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Min Area (m²)</label>
                    <input
                        type="number"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-accent focus:border-accent"
                        placeholder="0"
                        onChange={(e) => handleChange('min_area', e.target.value)}
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Rooms</label>
                    <select
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-accent focus:border-accent"
                        onChange={(e) => handleChange('rooms', e.target.value)}
                    >
                        <option value="">Any</option>
                        <option value="1">1+</option>
                        <option value="2">2+</option>
                        <option value="3">3+</option>
                        <option value="4">4+</option>
                        <option value="5">5+</option>
                    </select>
                </div>
            </div>
        </div>
    );
}
