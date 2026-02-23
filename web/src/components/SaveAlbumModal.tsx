
"use client";

import React, { useState } from 'react';
import { createAlbum, SearchFilters } from '@/lib/api';
import { useRouter } from 'next/navigation';

interface SaveAlbumModalProps {
    isOpen: boolean;
    onClose: () => void;
    currentQuery: string;
    currentFilters: SearchFilters;
}

export default function SaveAlbumModal({ isOpen, onClose, currentQuery, currentFilters }: SaveAlbumModalProps) {
    const [albumName, setAlbumName] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const router = useRouter();

    if (!isOpen) return null;

    const handleSave = async () => {
        if (!albumName.trim()) {
            setError('Please enter an album name');
            return;
        }

        setIsSubmitting(true);
        setError(null);

        try {
            const queryJson = JSON.stringify({
                query: currentQuery,
                filters: currentFilters,
                top_k: 100 // Reasonable default for dynamic albums
            });

            const albumId = await createAlbum(albumName, true, queryJson);
            onClose();
            router.push(`/albums/${albumId}`);
        } catch (err) {
            console.error('Failed to save album:', err);
            setError('Failed to save album. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
                <div className="p-6">
                    <h2 className="text-xl font-semibold text-white mb-2">Save as Smart Album</h2>
                    <p className="text-zinc-400 text-sm mb-6">
                        Smart albums automatically update whenever new files match your search criteria.
                    </p>

                    <div className="space-y-4">
                        <div>
                            <label htmlFor="albumName" className="block text-sm font-medium text-zinc-300 mb-1.5">
                                Album Name
                            </label>
                            <input
                                id="albumName"
                                type="text"
                                value={albumName}
                                onChange={(e) => setAlbumName(e.target.value)}
                                placeholder="e.g., My Favorite Landscapes"
                                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2.5 text-white placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                                autoFocus
                            />
                        </div>

                        {error && (
                            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                                {error}
                            </div>
                        )}

                        <div className="bg-zinc-800/30 rounded-xl p-4 border border-zinc-800/50">
                            <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">Query Preview</h3>
                            <div className="text-sm text-zinc-300 italic truncate">"{currentQuery}"</div>
                            {(currentFilters.tags?.length || currentFilters.character_tags?.length || currentFilters.series_tags?.length) && (
                                <div className="mt-2 flex flex-wrap gap-1.5">
                                    {[...(currentFilters.tags || []), ...(currentFilters.character_tags || []), ...(currentFilters.series_tags || [])].map((filter, i) => (
                                        <span key={i} className="px-2 py-0.5 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] rounded-full">
                                            {filter}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="flex items-center justify-end gap-3 p-6 bg-zinc-950/50 border-t border-zinc-800">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-zinc-400 hover:text-white transition-colors"
                        disabled={isSubmitting}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={isSubmitting || !albumName.trim()}
                        className="px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white font-medium rounded-xl transition-all shadow-lg shadow-blue-600/20 flex items-center gap-2"
                    >
                        {isSubmitting && (
                            <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                        )}
                        Save Album
                    </button>
                </div>
            </div>
        </div>
    );
}
