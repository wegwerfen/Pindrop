import { useQuery } from '@tanstack/react-query'
import { fetchTags } from '@/lib/api'

export function useTags() {
  return useQuery({
    queryKey: ['tags'],
    queryFn: fetchTags,
    staleTime: 60_000,
  })
}
