import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { cancelJob, getJobStatus } from '@/api/client'
import { getJobHistory, removeJobFromHistory, type HistoryEntry } from '@/hooks/useJobHistory'
import { Button } from '@/components/ui/Button'

function JobRow({
  entry,
  onRemove,
  index,
  total,
}: {
  entry: HistoryEntry
  onRemove: () => void
  index: number
  total: number
}) {
  const { data, isError } = useQuery({
    queryKey: ['job', entry.job_id],
    queryFn: () => getJobStatus(entry.job_id),
    retry: false,
    staleTime: 2_000,
    refetchInterval: (q) => {
      const status = q.state.data?.status
      if (!status) return 3_000
      return status === 'done' || status === 'error' ? false : 3_000
    },
  })

  const expired = isError || (data?.status === 'error' && !data?.error_message)
  const date = new Date(entry.created_at).toLocaleString()
  const isImagePhase =
    !!data &&
    !isError &&
    (data.status === 'downloading_images' ||
      (data.status === 'generating' && data.images_found > 0 && data.images_embedded < data.images_found))
  const displayStatus = isImagePhase ? 'downloading_images' : data?.status

  return (
    <tr className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50">
      <td className="py-3 px-4">
        <div className="font-medium text-gray-900 dark:text-white text-sm truncate max-w-xs">
          {entry.title}
        </div>
        <div className="text-xs text-gray-400 mt-0.5">{date}</div>
        {entry.source_url && (
          <div className="text-xs text-gray-400 truncate max-w-xs">{entry.source_url}</div>
        )}
      </td>
      <td className="py-3 px-4">
        <div className="space-y-0.5">
          <StatusBadge status={displayStatus} isError={isError} prefix={`${index}/${total}.`} />
          {data &&
            !isError &&
            data.status !== 'done' &&
            data.status !== 'error' &&
            (isImagePhase ? data.images_found > 0 : data.posts_found > 0) && (
              <p className="text-[11px] text-gray-500 dark:text-gray-400">
                {isImagePhase
                  ? `(${data.images_embedded}/${data.images_found})`
                  : `(${data.posts_crawled}/${data.posts_found})`}
              </p>
            )}
        </div>
      </td>
      <td className="py-3 px-4 text-sm text-gray-600 dark:text-gray-400">
        {data?.status === 'done' && data.posts_crawled > 0
          ? data.posts_crawled
          : data?.status === 'done'
          ? '—'
          : null}
      </td>
      <td className="py-3 px-4">
        {data?.status === 'done' ? (
          <div className="flex gap-2 flex-wrap">
            {data.has_epub && (
              <a
                href={`/api/jobs/${entry.job_id}/download/epub`}
                download
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium"
              >
                EPUB
              </a>
            )}
            {data.has_mobi && (
              <a
                href={`/api/jobs/${entry.job_id}/download/mobi`}
                download
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium"
              >
                MOBI
              </a>
            )}
            {data.has_pdf && (
              <a
                href={`/api/jobs/${entry.job_id}/download/pdf`}
                download
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium"
              >
                PDF
              </a>
            )}
          </div>
        ) : expired ? (
          <span className="text-xs text-gray-400">Expired</span>
        ) : data ? (
          <Link
            to={`/working/${entry.job_id}`}
            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          >
            View progress →
          </Link>
        ) : null}
      </td>
      <td className="py-3 px-4 text-right">
        <button
          onClick={onRemove}
          className="text-xs text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
          aria-label="Remove from history"
        >
          ✕
        </button>
      </td>
    </tr>
  )
}

function StatusBadge({
  status,
  isError,
  prefix,
}: {
  status?: string
  isError?: boolean
  prefix?: string
}) {
  if (isError || !status) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
        expired
      </span>
    )
  }

  const styles: Record<string, string> = {
    done: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    error: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    queued: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    parsing: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    crawling: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    downloading_images: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    generating: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  }
  const labels: Record<string, string> = {
    downloading_images: 'downloading images',
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${styles[status] ?? styles.queued}`}
    >
      {prefix ? `${prefix} ` : ''}
      {labels[status] ?? status}
    </span>
  )
}

export function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [cancelState, setCancelState] = useState<
    Record<string, 'ok' | 'local' | 'pending' | undefined>
  >({})

  useEffect(() => {
    setEntries(getJobHistory())
  }, [])

  async function handleRemove(job_id: string) {
    setCancelState((prev) => ({ ...prev, [job_id]: 'pending' }))
    const cancelled = await cancelJob(job_id).then(
      () => true,
      () => false,
    )
    setCancelState((prev) => ({ ...prev, [job_id]: cancelled ? 'ok' : 'local' }))
    removeJobFromHistory(job_id)
    setEntries((prev) => prev.filter((e) => e.job_id !== job_id))
    window.setTimeout(() => setCancelState((prev) => ({ ...prev, [job_id]: undefined })), 2000)
  }

  async function handleClearAll() {
    await Promise.all(entries.map((e) => cancelJob(e.job_id).catch(() => undefined)))
    entries.forEach((e) => removeJobFromHistory(e.job_id))
    setEntries([])
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-12 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Your ebooks</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Saved in this browser. Files expire after 24 hours.
          </p>
          {Object.values(cancelState).includes('ok') && (
            <p className="text-xs text-green-600 dark:text-green-400 mt-1">
              ✅ Task removed and cancelled in backend.
            </p>
          )}
          {Object.values(cancelState).includes('local') && (
            <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
              ⚠️ Removed locally, backend cancellation could not be confirmed.
            </p>
          )}
        </div>
        {entries.length > 0 && (
          <Button variant="secondary" onClick={() => void handleClearAll()}>
            Clear all
          </Button>
        )}
      </div>

      {entries.length === 0 ? (
        <div className="text-center py-24 text-gray-400 dark:text-gray-500 space-y-3">
          <p className="text-4xl">📚</p>
          <p className="text-sm">No ebooks yet. Convert a blog to get started.</p>
          <Link to="/" className="text-sm text-blue-600 dark:text-blue-400 hover:underline">
            Convert a blog →
          </Link>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-gray-50 dark:bg-gray-800/60 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              <tr>
                <th className="py-2.5 px-4">Blog / Feed</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4">Posts</th>
                <th className="py-2.5 px-4">Downloads</th>
                <th className="py-2.5 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, i) => (
                <JobRow
                  key={entry.job_id}
                  entry={entry}
                  index={i}
                  total={entries.length}
                  onRemove={() => void handleRemove(entry.job_id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  )
}
