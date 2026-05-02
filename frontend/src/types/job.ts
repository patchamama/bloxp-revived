export type JobStatus =
  | 'queued'
  | 'parsing'
  | 'crawling'
  | 'downloading_images'
  | 'generating'
  | 'done'
  | 'error'

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
  ebook_title?: string
  source_url?: string
  images_found: number
  images_embedded: number
  queue_position?: number
}
