import { useQuery } from '@tanstack/react-query'
import { fetchArtifacts, searchArtifacts } from '@/lib/api'
import { useFilterStore } from '@/store/filterStore'

export function useArtifacts() {
  const { searchQuery, selectedTagId, selectedCollectionId, sort } = useFilterStore()
  const isSearchMode = searchQuery.trim().length > 0

  const listQuery = useQuery({
    queryKey: ['artifacts', { selectedTagId, selectedCollectionId, sort }],
    queryFn: () =>
      fetchArtifacts({
        tag_id: selectedTagId ?? undefined,
        collection_id: selectedCollectionId ?? undefined,
        sort,
      }),
    enabled: !isSearchMode,
    staleTime: 30_000,
  })

  const searchResult = useQuery({
    queryKey: ['artifacts', 'search', searchQuery],
    queryFn: () => searchArtifacts(searchQuery.trim()),
    enabled: isSearchMode,
    staleTime: 15_000,
  })

  return isSearchMode ? searchResult : listQuery
}
