
'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { Search, Filter, Layers, Users, LayoutGrid } from 'lucide-react';
import { cn } from '@/lib/utils';

const fetchFilters = async () => {
    const res = await fetch('/api/gallery/filters');
    if (!res.ok) return { characters: [], series: [] };
    return res.json();
};

function SidebarContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const pathname = usePathname();

    const { data: filters } = useQuery({ queryKey: ['filters'], queryFn: fetchFilters });

    const [query, setQuery] = useState('');
    const [character, setCharacter] = useState('All');
    const [series, setSeries] = useState('All');

    useEffect(() => {
        setQuery(searchParams.get('q') || '');
        setCharacter(searchParams.get('character') || 'All');
        setSeries(searchParams.get('series') || 'All');
    }, [searchParams]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        const params = new URLSearchParams(searchParams);
        if (query) params.set('q', query);
        else params.delete('q');

        // Reset page logic handled by filters (queryKey change)
        router.push(`${pathname}?${params.toString()}`);
    };

    const updateFilter = (key: string, value: string) => {
        const params = new URLSearchParams(searchParams);
        if (value && value !== 'All') params.set(key, value);
        else params.delete(key);

        router.push(`${pathname}?${params.toString()}`);
    }

    return (
        <aside className="fixed left-0 top-16 bottom-0 w-64 bg-black/95 backdrop-blur border-r border-white/10 p-4 overflow-y-auto z-40">
            <form onSubmit={handleSearch} className="mb-6 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                    type="text"
                    placeholder="Search..."
                    className="w-full bg-white/5 border border-white/10 rounded-full py-2 pl-9 pr-4 text-sm focus:outline-none focus:border-blue-500 transition-colors text-white"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                />
            </form>

            <div className="space-y-6">
                <div>
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                        <Filter className="w-3 h-3" /> Filters
                    </h3>
                    <div className="space-y-4">
                        {/* Characters */}
                        <div>
                            <label className="text-xs text-gray-400 mb-1 block">Character</label>
                            <select
                                className="w-full bg-white/5 border border-white/10 rounded px-2 py-2 text-sm outline-none text-white appearance-none cursor-pointer"
                                value={character}
                                onChange={(e) => updateFilter('character', e.target.value)}
                            >
                                <option value="All">All Characters</option>
                                {filters?.characters.map((c: string) => (
                                    <option key={c} value={c}>{c}</option>
                                ))}
                            </select>
                        </div>

                        {/* Series */}
                        <div>
                            <label className="text-xs text-gray-400 mb-1 block">Series</label>
                            <select
                                className="w-full bg-white/5 border border-white/10 rounded px-2 py-2 text-sm outline-none text-white appearance-none cursor-pointer"
                                value={series}
                                onChange={(e) => updateFilter('series', e.target.value)}
                            >
                                <option value="All">All Series</option>
                                {filters?.series.map((s: string) => (
                                    <option key={s} value={s}>{s}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>

                <div>
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                        <Layers className="w-3 h-3" /> Navigation
                    </h3>
                    <nav className="space-y-1">
                        <Link href="/" className={cn("flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors", pathname === '/' ? "bg-white/10 text-white" : "text-gray-400 hover:text-white hover:bg-white/5")}>
                            <LayoutGrid className="w-4 h-4" /> Gallery
                        </Link>
                        <Link href="/clusters" className={cn("flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors", pathname === '/clusters' ? "bg-white/10 text-white" : "text-gray-400 hover:text-white hover:bg-white/5")}>
                            <Users className="w-4 h-4" /> Face Clusters
                        </Link>
                    </nav>
                </div>
            </div>
        </aside>
    );
}

export default function Sidebar() {
    return (
        <Suspense fallback={<div className="w-64 bg-black/95"></div>}>
            <SidebarContent />
        </Suspense>
    )
}
