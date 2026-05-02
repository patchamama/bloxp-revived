import { useQuery } from '@tanstack/react-query'
import { getSystemStatus } from '@/api/client'

export function useSystemStatus() {
  return useQuery({
    queryKey: ['system-status'],
    queryFn: getSystemStatus,
    refetchInterval: 5000,
    retry: 1,
  })
}
