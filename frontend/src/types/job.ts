export type JobStatus = 'queued' | 'parsing' | 'crawling' | 'generating' | 'done' | 'error'

export interface JobStatusResponse {
  job_id: string
  status: JobStatus
  progress: number
  posts_found: number
  posts_crawled: number
  error_message?: string
  has_epub: boolean
  has_mobi: boolean
  has_pdf: boolean
}
