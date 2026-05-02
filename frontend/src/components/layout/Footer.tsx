import { useSystemStatus } from '@/hooks/useSystemStatus'
import pkg from '../../../package.json'

export function Footer() {
  const { data } = useSystemStatus()

  return (
    <footer className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 py-5 text-center text-xs text-gray-500 dark:text-gray-400 space-y-1">
      <p>© {new Date().getFullYear()} Bloxp Revived — Convert your blog to an ebook</p>
      <p className="opacity-70">
        FE v{pkg.version} · BE v{data?.backend_version ?? '—'} · Celery{' '}
        {data?.celery_running ? `online (${data.celery_workers})` : 'offline'} · Running{' '}
        {data?.active_jobs ?? 0}/{data?.max_concurrent_jobs ?? 0} · Pending {data?.pending_jobs ?? 0}
      </p>
    </footer>
  )
}
