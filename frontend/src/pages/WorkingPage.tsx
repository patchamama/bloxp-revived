import { useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useJobStatus } from '@/hooks/useJobStatus'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { Spinner } from '@/components/ui/Spinner'
import { ErrorPanel } from '@/components/ui/ErrorPanel'
import { Button } from '@/components/ui/Button'
import { addJobToHistory } from '@/hooks/useJobHistory'
import type { JobStatus } from '@/types/job'

const STATUS_MESSAGES: Record<JobStatus, string> = {
  queued: 'Your job is in the queue…',
  parsing: 'Parsing feed…',
  crawling: 'Crawling blog posts…',
  downloading_images: 'Generating ebook…',
  generating: 'Generating ebook…',
  done: 'Your ebook is ready!',
  error: 'An error occurred.',
}

export function WorkingPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const { data, isLoading, isError } = useJobStatus(jobId ?? null)

  useEffect(() => {
    if (data?.status === 'done' && jobId && data.ebook_title) {
      addJobToHistory(jobId, data.ebook_title)
    }
  }, [data?.status, data?.ebook_title, jobId])

  if (isLoading || !data) {
    return (
      <main className="max-w-2xl mx-auto px-4 py-24 flex flex-col items-center gap-4">
        <Spinner size="lg" />
        <p className="text-gray-500 dark:text-gray-400">Loading job status…</p>
      </main>
    )
  }

  if (isError) {
    return (
      <main className="max-w-2xl mx-auto px-4 py-16 space-y-4">
        <ErrorPanel message="Could not load job status. The job may have expired." />
        <Link
          to="/"
          className="inline-block text-blue-600 dark:text-blue-400 hover:underline text-sm"
        >
          ← Try again
        </Link>
      </main>
    )
  }

  const queuePos = Number(data.queue_position ?? 0)
  const hasQueuePos = Number.isFinite(queuePos) && queuePos > 0

  return (
    <main className="max-w-2xl mx-auto px-4 py-16 space-y-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {data.status === 'queued' && hasQueuePos
            ? `Position ${queuePos} in queue…`
            : STATUS_MESSAGES[data.status]}
        </h1>
        {data.status === 'queued' && hasQueuePos && (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {queuePos === 1
              ? "You're next — processing will start soon."
              : `${queuePos - 1} job${queuePos - 1 > 1 ? 's' : ''} ahead of you.`}
          </p>
        )}
        {data.status === 'queued' && !hasQueuePos && (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Waiting for an available worker…
          </p>
        )}
        {data.status === 'crawling' && data.posts_found > 0 && (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {data.posts_crawled} / {data.posts_found} posts crawled
            {data.posts_cached > 0 ? ` (cached: ${data.posts_cached})` : ''}
          </p>
        )}
        {(data.status === 'downloading_images' || data.status === 'generating') &&
          data.images_found > 0 && (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Embedding images: {data.images_embedded} / {data.images_found}
            {data.images_cached > 0 ? ` (cached: ${data.images_cached})` : ''}
          </p>
        )}
      </div>

      {data.status === 'queued' ? <Spinner /> : <ProgressBar value={data.progress} />}

      {data.status === 'done' && (
        <div className="space-y-3">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Download your ebook:
          </p>
          <div className="flex flex-wrap gap-3">
            {data.has_epub && (
              <a href={`/api/jobs/${jobId}/download/epub`} download>
                <Button variant="primary">Download EPUB</Button>
              </a>
            )}
            {data.has_mobi && (
              <a href={`/api/jobs/${jobId}/download/mobi`} download>
                <Button variant="secondary">Download MOBI</Button>
              </a>
            )}
            {data.has_pdf && (
              <a href={`/api/jobs/${jobId}/download/pdf`} download>
                <Button variant="secondary">Download PDF</Button>
              </a>
            )}
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 pt-1">
            Files are available for 24 hours.
          </p>
        </div>
      )}

      {data.status === 'error' && (
        <div className="space-y-4">
          <ErrorPanel message={data.error_message ?? 'An unknown error occurred.'} />
          <Link
            to="/"
            className="inline-block text-blue-600 dark:text-blue-400 hover:underline text-sm"
          >
            ← Try again
          </Link>
        </div>
      )}
    </main>
  )
}
