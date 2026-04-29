import { useQuery } from '@tanstack/react-query'
import { getJobStatus } from '@/api/client'
import type { JobStatus } from '@/types/job'

const TERMINAL: JobStatus[] = ['done', 'error']

export function useJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: jobId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (!status || TERMINAL.includes(status)) return false
      return 2000
    },
  })
}
