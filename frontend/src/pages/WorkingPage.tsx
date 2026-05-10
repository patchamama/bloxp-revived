import { useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useJobStatus } from '@/hooks/useJobStatus'
import { useDynamicFavicon } from '@/hooks/useDynamicFavicon'
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
  downloading_images: 'Embedding images…',
  compacting_epub: 'Compacting content for EPUB…',
  converting_mobi: 'Converting EPUB to MOBI…',
  generating_pdf: 'Generating PDF…',
  generating: 'Generating ebook…',
  done: 'Your ebook is ready!',
  error: 'An error occurred.',
}

const APP = 'Bloxp'
const BASE = import.meta.env.BASE_URL.replace(/\/$/, '')

export function WorkingPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const { data, isLoading, isError } = useJobStatus(jobId ?? null)

  useDynamicFavicon(data?.status ?? null, data?.progress ?? 0)

  useEffect(() => {
    if (data?.status === 'done' && jobId && data.ebook_title) {
      addJobToHistory(jobId, data.ebook_title)
    }
  }, [data?.status, data?.ebook_title, jobId])

  useEffect(() => {
    if (!data) return
    const { status, progress, queue_position } = data
    let title: string
    if (status === 'queued') {
      title = queue_position ? `[#${queue_position}] ${APP}` : `[cola] ${APP}`
    } else if (status === 'done') {
      title = `[✓] ${APP}`
    } else if (status === 'error') {
      title = `[✗] ${APP}`
    } else {
      title = `[${Math.round(progress)}%] ${APP}`
    }
    document.title = title
    return () => { document.title = APP }
  }, [data?.status, data?.progress, data?.queue_position])

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
        {(data.status === 'downloading_images') &&
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
              <a href={`${BASE}/api/jobs/${jobId}/download/epub`} download>
                <Button variant="primary">Download EPUB</Button>
              </a>
            )}
            {data.has_mobi && (
              <a href={`${BASE}/api/jobs/${jobId}/download/mobi`} download>
                <Button variant="secondary">Download MOBI</Button>
              </a>
            )}
            {data.has_pdf && (
              <a href={`${BASE}/api/jobs/${jobId}/download/pdf`} download>
                <Button variant="secondary">Download PDF</Button>
              </a>
            )}
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 pt-1">
            Files are available for 24 hours.
          </p>
          {data.posts_skipped > 0 && (
            <details className="mt-4 rounded-lg border border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/20 p-3">
              <summary className="cursor-pointer text-sm font-medium text-yellow-800 dark:text-yellow-300">
                ⚠ {data.posts_skipped} post{data.posts_skipped > 1 ? 's' : ''} could not be downloaded
              </summary>
              <ul className="mt-2 space-y-1 max-h-48 overflow-y-auto">
                {data.skipped_urls.map((url) => (
                  <li key={url} className="text-xs text-yellow-700 dark:text-yellow-400 truncate">
                    <a href={url} target="_blank" rel="noreferrer" className="hover:underline">
                      {url}
                    </a>
                  </li>
                ))}
              </ul>
            </details>
          )}
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
