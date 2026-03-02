/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                brand: {
                    50:  '#eff6ff',
                    100: '#dbeafe',
                    200: '#bfdbfe',
                    500: '#3b82f6',
                    600: '#2563eb',
                    700: '#1d4ed8',
                    900: '#1e3a8a',
                },
                canvas: '#f8fafc',
                surface: '#ffffff',
                deal: {
                    great: '#059669',   // emerald-600
                    good:  '#10b981',   // emerald-500
                    fair:  '#64748b',   // slate-500
                    high:  '#f59e0b',   // amber-500
                    over:  '#ef4444',   // red-500
                },
            },
            boxShadow: {
                card: '0 1px 3px 0 rgba(0,0,0,0.06), 0 1px 2px -1px rgba(0,0,0,0.04)',
                'card-hover': '0 4px 12px 0 rgba(0,0,0,0.08), 0 2px 4px -2px rgba(0,0,0,0.05)',
                panel: '2px 0 8px 0 rgba(0,0,0,0.04)',
            },
            fontSize: {
                '2xs': ['0.65rem', { lineHeight: '1rem' }],
            },
        },
    },
    plugins: [],
}
