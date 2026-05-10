export type JobStatus =
  | 'queued'
  | 'parsing'
  | 'crawling'
  | 'downloading_images'
  | 'compacting_epub'
  | 'converting_mobi'
  | 'generating_pdf'
  | 'generating'
  | 'done'
  | 'error'

export interface JobStatusResponse {
  job_id: string
  status: JobStatus
  progress: number
  posts_found: number
  posts_crawled: number
  posts_cached: number
  posts_skipped: number
  skipped_urls: string[]
  error_message?: string
  has_epub: boolean
  has_mobi: boolean
  has_pdf: boolean
  ebook_title?: string
  source_url?: string
  images_found: number
  images_embedded: number
  images_cached: number
  queue_position?: number
}
