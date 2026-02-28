import { create } from 'zustand'
import type { SortOption } from '@/lib/api'

interface FilterState {
  searchQuery: string
  selectedTagId: string | null
  selectedCollectionId: string | null
  sort: SortOption
  setSearchQuery: (q: string) => void
  setSelectedTagId: (id: string | null) => void
  setSelectedCollectionId: (id: string | null) => void
  setSort: (sort: SortOption) => void
  clearFilters: () => void
}

export const useFilterStore = create<FilterState>((set) => ({
  searchQuery: '',
  selectedTagId: null,
  selectedCollectionId: null,
  sort: 'captured_at_desc',

  setSearchQuery: (q) => set({ searchQuery: q }),
  setSelectedTagId: (id) => set({ selectedTagId: id, selectedCollectionId: null }),
  setSelectedCollectionId: (id) => set({ selectedCollectionId: id, selectedTagId: null }),
  setSort: (sort) => set({ sort }),
  clearFilters: () => set({ searchQuery: '', selectedTagId: null, selectedCollectionId: null }),
}))
