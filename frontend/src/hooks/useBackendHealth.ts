import { useQuery } from '@tanstack/react-query'
import { getHealth } from '@/api/client'

export function useBackendHealth() {
  return useQuery({
    queryKey: ['backend-health'],
    queryFn: getHealth,
    staleTime: 60_000,
  })
}
