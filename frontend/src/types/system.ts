export type SystemStatusResponse = {
  backend_version: string
  celery_running: boolean
  celery_workers: number
  active_jobs: number
  pending_jobs: number
  max_concurrent_jobs: number
}
