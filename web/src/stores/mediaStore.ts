import { create } from 'zustand'
import { MediaItem } from '@/lib/api'

interface MediaState {
    selectedItem: MediaItem | null;
    isPlaying: boolean;
    currentTime: number;
    duration: number;
    volume: number;
    playbackRate: number;

    // Actions
    setSelectedItem: (item: MediaItem | null) => void;
    setIsPlaying: (playing: boolean) => void;
    setCurrentTime: (time: number) => void;
    setDuration: (duration: number) => void;
    setVolume: (volume: number) => void;
    setPlaybackRate: (rate: number) => void;

    // Global Commands (for syncing across components)
    seekTo: (time: number) => void;
    play: () => void;
    pause: () => void;
}

export const useMediaStore = create<MediaState>()((set) => ({
    selectedItem: null,
    isPlaying: false,
    currentTime: 0,
    duration: 0,
    volume: 1,
    playbackRate: 1,

    setSelectedItem: (item: MediaItem | null) => set({ selectedItem: item }),
    setIsPlaying: (playing: boolean) => set({ isPlaying: playing }),
    setCurrentTime: (time: number) => set({ currentTime: time }),
    setDuration: (duration: number) => set({ duration: duration }),
    setVolume: (volume: number) => set({ volume }),
    setPlaybackRate: (rate: number) => set({ playbackRate: rate }),

    seekTo: (time: number) => {
        set({ currentTime: time });
        // Components should listen to this change and update their video element
        window.dispatchEvent(new CustomEvent('lcp:media-seek', { detail: { time } }));
    },
    play: () => {
        set({ isPlaying: true });
        window.dispatchEvent(new CustomEvent('lcp:media-play'));
    },
    pause: () => {
        set({ isPlaying: false });
        window.dispatchEvent(new CustomEvent('lcp:media-pause'));
    }
}))
