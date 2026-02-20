
'use client';

import { useInfiniteQuery } from '@tanstack/react-query';
import { useInView } from 'react-intersection-observer';
import { useEffect, Suspense } from 'react';
import Image from 'next/image';
import { useSearchParams } from 'next/navigation';
import { cn } from '@/lib/utils';

type MediaItem = {
    id: number;
    file_path: string;
    media_type: string;
    width: number | null;
    height: number | null;
    tags: string[];
    character_tags: string[];
    series_tags: string[];
};

const fetchGallery = async ({ pageParam = 0, queryKey }: any) => {
    const [_, { q, character, series, media_type }] = queryKey;

    if (q) {
        const res = await fetch(`/api/gallery/search?query=${encodeURIComponent(q)}&top_k=50`, {
            method: 'POST'
        });
        if (!res.ok) throw new Error('Network response was not ok');
        const items = await res.json();
        // Search results are flat list, treat as single page at 0
        if (pageParam === 0) return items;
        return [];
    }

    const params = new URLSearchParams();
    params.set('limit', '50');
    params.set('offset', pageParam.toString());
    if (character && character !== 'All') params.set('character', character);
    if (series && series !== 'All') params.set('series', series);
    if (media_type) params.set('media_type', media_type);

    const res = await fetch(`/api/gallery/?${params.toString()}`);
    if (!res.ok) throw new Error('Network response was not ok');
    return res.json();
};

function GalleryContent() {
    const { ref, inView } = useInView();
    const searchParams = useSearchParams();

    const q = searchParams.get('q');
    const character = searchParams.get('character');
    const series = searchParams.get('series');
    const media_type = searchParams.get('media_type');

    const { data, fetchNextPage, hasNextPage, isFetchingNextPage, status } = useInfiniteQuery({
        queryKey: ['gallery', { q, character, series, media_type }],
        queryFn: fetchGallery,
        getNextPageParam: (lastPage, allPages) => {
            // Stop pagination if search results (single page)
            if (q) return undefined;

            if (lastPage.length < 50) return undefined;
            return allPages.length * 50;
        },
        initialPageParam: 0
    });

    useEffect(() => {
        if (inView && hasNextPage) {
            fetchNextPage();
        }
    }, [inView, hasNextPage, fetchNextPage]);

    const items = data?.pages.flat() as MediaItem[] || [];

    if (status === 'pending') return <div className="p-10 text-center text-white">Loading Gallery...</div>;
    if (status === 'error') return <div className="p-10 text-center text-red-500">Error loading gallery</div>;

    return (
        <div className="columns-2 md:columns-3 lg:columns-4 xl:columns-5 gap-4 p-4 space-y-4 pb-20">
            {items.map((item) => (
                <div key={item.id} className="break-inside-avoid mb-4 relative group rounded-xl overflow-hidden bg-gray-900 shadow-md">
                    {item.width && item.height ? (
                        <Image
                            src={`http://localhost:8000/media/${item.id}/thumbnail`}
                            alt={item.file_path}
                            width={item.width}
                            height={item.height}
                            className="w-full h-auto object-cover transition-transform duration-300 group-hover:scale-105"
                            unoptimized
                        />
                    ) : (
                        <div className="aspect-square bg-gray-800 flex items-center justify-center text-gray-500">
                            No Preview
                        </div>
                    )}

                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-3">
                        <p className="text-white text-xs truncate font-medium">{item.file_path.split(/[\\/]/).pop()}</p>
                        <div className="flex gap-1 flex-wrap mt-1">
                            {item.character_tags.slice(0, 2).map(t => (
                                <span key={t} className="text-[10px] bg-blue-600/80 px-1.5 py-0.5 rounded text-white">{t}</span>
                            ))}
                            {item.media_type === 'video' && <span className="text-[10px] bg-red-600/80 px-1.5 py-0.5 rounded text-white">Video</span>}
                        </div>
                    </div>
                </div>
            ))}

            <div ref={ref} className="col-span-full h-20 flex justify-center items-center py-4">
                {(isFetchingNextPage) && <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>}
                {!hasNextPage && items.length > 0 && <div className="text-gray-500 text-sm">End of Collection</div>}
            </div>
        </div>
    );
}

export default function Gallery() {
    return (
        <Suspense fallback={<div className="p-10 text-center text-gray-500">Initializing Gallery...</div>}>
            <GalleryContent />
        </Suspense>
    )
}
