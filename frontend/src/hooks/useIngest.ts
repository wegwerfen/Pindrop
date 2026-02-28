import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ingestUrl } from '@/lib/api'

export function useIngest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ingestUrl,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artifacts'] })
    },
  })
}
