import { useParams, Link } from 'react-router-dom'
import { useJobStatus } from '@/hooks/useJobStatus'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { Spinner } from '@/components/ui/Spinner'
import { ErrorPanel } from '@/components/ui/ErrorPanel'
import { Button } from '@/components/ui/Button'
import type { JobStatus } from '@/types/job'

const STATUS_MESSAGES: Record<JobStatus, string> = {
  queued: 'Your job is in the queue…',
  parsing: 'Parsing feed…',
  crawling: 'Crawling blog posts…',
  generating: 'Generating ebook…',
  done: 'Your ebook is ready!',
  error: 'An error occurred.',
}

export function WorkingPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const { data, isLoading, isError } = useJobStatus(jobId ?? null)

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

  return (
    <main className="max-w-2xl mx-auto px-4 py-16 space-y-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {STATUS_MESSAGES[data.status]}
        </h1>
        {data.status === 'crawling' && data.posts_found > 0 && (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {data.posts_crawled} / {data.posts_found} posts crawled
          </p>
        )}
      </div>

      <ProgressBar value={data.progress} />

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
