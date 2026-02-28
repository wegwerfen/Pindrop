import { useQuery } from '@tanstack/react-query'
import { fetchCollections } from '@/lib/api'

export function useCollections() {
  return useQuery({
    queryKey: ['collections'],
    queryFn: fetchCollections,
    staleTime: 60_000,
  })
}
