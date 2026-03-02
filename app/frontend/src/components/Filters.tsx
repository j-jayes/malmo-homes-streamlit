import type { Filters as FilterType } from '../api/client';
import { SlidersHorizontal } from 'lucide-react';

interface FiltersProps {
    filters: FilterType;
    onChange: (filters: FilterType) => void;
}

const inputCls =
    'w-full px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg ' +
    'text-slate-800 placeholder:text-slate-400 ' +
    'focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 ' +
    'transition-colors';

export function Filters({ filters, onChange }: FiltersProps) {
    const set = (key: keyof FilterType, value: string) => {
        onChange({ ...filters, [key]: value ? Number(value) : undefined });
    };

    return (
        <div className="space-y-3">
            <div className="flex items-center gap-1.5">
                <SlidersHorizontal size={13} className="text-slate-400" />
                <span className="text-xs font-semibold text-slate-600">Filters</span>
            </div>

            {/* Price range */}
            <div>
                <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Price (SEK)
                </label>
                <div className="grid grid-cols-2 gap-2">
                    <input
                        type="number"
                        className={inputCls}
                        placeholder="Min"
                        onChange={(e) => set('min_price', e.target.value)}
                    />
                    <input
                        type="number"
                        className={inputCls}
                        placeholder="Max"
                        onChange={(e) => set('max_price', e.target.value)}
                    />
                </div>
            </div>

            {/* Area + Rooms */}
            <div className="grid grid-cols-2 gap-2">
                <div>
                    <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                        Min area m²
                    </label>
                    <input
                        type="number"
                        className={inputCls}
                        placeholder="Any"
                        onChange={(e) => set('min_area', e.target.value)}
                    />
                </div>
                <div>
                    <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                        Rooms
                    </label>
                    <select
                        className={inputCls}
                        onChange={(e) => set('rooms', e.target.value)}
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
