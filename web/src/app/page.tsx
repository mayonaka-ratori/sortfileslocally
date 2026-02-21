"use client"

import { useEffect, useState } from "react"
import { MediaItem, fetchMedia, searchMedia } from "@/lib/api"
import { GalleryGrid } from "@/components/GalleryGrid"
import { ChatPanel } from "@/components/ChatPanel"
import { Sidebar, FilterState } from "@/components/Sidebar"

export default function Home() {
  const [media, setMedia] = useState<MediaItem[]>([])
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [filters, setFilters] = useState<FilterState>({})
  const [currentSearch, setCurrentSearch] = useState("")

  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  useEffect(() => {
    if (!currentSearch) {
      setOffset(0)
      loadMedia(0, filters)
    }
  }, [filters])

  const loadMedia = async (currentOffset: number = 0, currentFilters = filters) => {
    try {
      if (currentOffset === 0) {
        setLoading(true)
      } else {
        setIsLoadingMore(true)
      }

      const limit = 50
      const data = await fetchMedia({ ...currentFilters, offset: currentOffset, limit })
      if (currentOffset === 0) {
        setMedia(data)
      } else {
        setMedia(prev => [...prev, ...data])
      }
      setHasMore(data.length === limit)
    } catch (err) {
      setError("Failed to load gallery.")
    } finally {
      if (currentOffset === 0) {
        setLoading(false)
      } else {
        setIsLoadingMore(false)
      }
    }
  }

  const handleLoadMore = () => {
    if (!currentSearch && hasMore && !loading && !isLoadingMore) {
      const nextOffset = offset + 50
      setOffset(nextOffset)
      loadMedia(nextOffset, filters)
    }
  }

  const handleSearch = async (query: string) => {
    setCurrentSearch(query)
    if (!query.trim()) {
      setOffset(0)
      loadMedia(0, filters)
      return
    }
    try {
      setLoading(true)
      const results = await searchMedia(query)

      // Client-side filtering of search results if filters are active
      let filteredResults = results;
      if (filters.media_type) {
        filteredResults = filteredResults.filter(r => r.media_type === filters.media_type)
      }
      if (filters.character) {
        filteredResults = filteredResults.filter(r => r.character_tags.includes(filters.character!))
      }
      if (filters.series) {
        filteredResults = filteredResults.filter(r => r.series_tags.includes(filters.series!))
      }

      setMedia(filteredResults)
      setSelectedItem(null) // Close chat on new search
      setHasMore(false) // Disable infinite scroll during semantic search
    } catch (err) {
      setError("Search failed.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="flex h-screen w-full bg-zinc-950 overflow-hidden font-sans">
      <Sidebar
        onFilterChange={setFilters}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 h-full relative border-r border-zinc-800">
        {loading ? (
          <div className="flex items-center justify-center h-full text-zinc-500">
            <div className="animate-pulse flex flex-col items-center">
              <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
              Loading Gallery...
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full text-red-500">
            {error}
          </div>
        ) : (
          <GalleryGrid
            media={media}
            onSelect={setSelectedItem}
            onSearch={handleSearch}
            onLoadMore={handleLoadMore}
            hasMore={hasMore}
            onMenuClick={() => setIsSidebarOpen(true)}
          />
        )}
      </div>

      {/* Chat / Context Panel */}
      {selectedItem && (
        <ChatPanel
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
        />
      )}
    </main>
  )
}
