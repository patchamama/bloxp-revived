import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  adminDeleteAllCache,
  adminDeleteAllEbooks,
  adminCacheSites,
  adminCacheStats,
  adminDeleteCacheEntry,
  adminDeleteCacheSite,
  adminDeleteEbook,
  adminEbooks,
  adminKillTask,
  adminLogin,
  adminTasks,
  adminRegenerateEbook,
  adminStatus,
} from '@/api/client'
import { addJobToHistory } from '@/hooks/useJobHistory'

const TOKEN_KEY = 'bloxp_admin_token'

function normalizeErrorMessage(err: unknown): string {
  const fallback = 'No se pudo iniciar sesión. Revisa tus credenciales e inténtalo de nuevo.'
  const raw = (err as any)?.message
  if (!raw || typeof raw !== 'string') return fallback

  if (raw.includes('Invalid credentials')) {
    return 'Usuario o contraseña incorrectos.'
  }

  try {
    const parsed = JSON.parse(raw)
    const detail = parsed?.detail
    if (typeof detail === 'string') {
      if (detail.toLowerCase().includes('invalid credentials')) {
        return 'Usuario o contraseña incorrectos.'
      }
      return detail
    }
  } catch {
    // no-op: raw is not JSON
  }

  return raw
}

function fmtDate(v: number | string | null | undefined): string {
  if (v == null) return '—'
  const n = typeof v === 'number' ? v : Number(v)
  if (!Number.isFinite(n)) return '—'
  const ms = n > 1e12 ? n : n * 1000
  return new Date(ms).toLocaleString()
}

function fmtBytes(n: number | null | undefined): string {
  if (!n || n <= 0) return '0 B'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(2)} MB`
}

function fmtCacheRatio(cached: number, total: number): string {
  if (!total || total <= 0) return '0/0 (0%)'
  const pct = Math.round((cached / total) * 100)
  return `${cached}/${total} (${pct}%)`
}

function timeLeftMeta(expiresAt: number | null | undefined): { text: string; cls: string } {
  if (!expiresAt || !Number.isFinite(Number(expiresAt))) {
    return { text: '—', cls: 'text-gray-500' }
  }
  const expSec = Number(expiresAt)
  const leftSec = Math.max(0, expSec - Date.now() / 1000)
  const hours = leftSec / 3600
  const text =
    leftSec <= 0
      ? 'expired'
      : hours >= 1
      ? `${hours.toFixed(1)}h left`
      : `${Math.ceil(leftSec / 60)}m left`
  const cls = leftSec <= 0 ? 'text-red-600' : hours <= 3 ? 'text-red-600' : hours <= 12 ? 'text-yellow-600' : 'text-green-600'
  return { text, cls }
}

function StatusBadge({ status }: { status?: string | null }) {
  const s = status ?? 'orphaned'
  const styles: Record<string, string> = {
    done: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    error: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    queued: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    parsing: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    crawling: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    downloading_images: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    compacting_epub: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    converting_mobi: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
    generating_pdf: 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/30 dark:text-fuchsia-400',
    generating: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    orphaned: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  }
  const labels: Record<string, string> = {
    downloading_images: 'downloading images',
    compacting_epub: 'compacting epub',
    converting_mobi: 'converting mobi',
    generating_pdf: 'generating pdf',
  }
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${styles[s] ?? styles.orphaned}`}>{labels[s] ?? s}</span>
}

export function AdminPage() {
  const navigate = useNavigate()
  const [token, setToken] = useState<string>(() => localStorage.getItem(TOKEN_KEY) ?? '')
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [status, setStatus] = useState<any>(null)
  const [cacheStats, setCacheStats] = useState<any>(null)
  const [cacheSites, setCacheSites] = useState<any[]>([])
  const [tasks, setTasks] = useState<{ running: any[]; pending: any[] }>({ running: [], pending: [] })
  const [openSite, setOpenSite] = useState<string | null>(null)
  const [ebooks, setEbooks] = useState<any[]>([])
  const [tab, setTab] = useState<'ebooks' | 'cache' | 'tasks'>('ebooks')
  const [filter, setFilter] = useState('')
  const [error, setError] = useState('')

  async function login() {
    setError('')
    try {
      const res = await adminLogin(username, password)
      localStorage.setItem(TOKEN_KEY, res.token)
      setToken(res.token)
    } catch (e: any) {
      setError(normalizeErrorMessage(e))
    }
  }

  async function loadAll() {
    if (!token) return
    setError('')
    const [s, cs, sites, eb, ts] = await Promise.allSettled([
      adminStatus(token),
      adminCacheStats(token),
      adminCacheSites(token),
      adminEbooks(token),
      adminTasks(token),
    ])
    if (s.status === 'fulfilled') setStatus(s.value)
    if (cs.status === 'fulfilled') setCacheStats(cs.value)
    if (sites.status === 'fulfilled') setCacheSites(sites.value.items)
    if (eb.status === 'fulfilled') setEbooks(eb.value.items)
    if (ts.status === 'fulfilled') setTasks(ts.value)

    const failures = [s, cs, sites, eb, ts].filter((r) => r.status === 'rejected')
    if (failures.length > 0) {
      setError(`Admin load partial: ${failures.length} request(s) failed`)
    }
  }

  useEffect(() => {
    if (!token) return
    void loadAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    if (!token || tab !== 'tasks') return
    const id = window.setInterval(() => {
      void loadAll()
    }, 5000)
    return () => window.clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, tab])

  const filteredEbooks = useMemo(() => {
    const q = filter.trim().toLowerCase()
    const sorted = [...ebooks].sort((a, b) => {
      const ae = Number(a?.expires_at ?? 0)
      const be = Number(b?.expires_at ?? 0)
      return ae - be
    })
    if (!q) return sorted
    return sorted.filter((e) => (
      String(e.ebook_title ?? '').toLowerCase().includes(q)
      || String(e.source_url ?? '').toLowerCase().includes(q)
      || String(e.job_id ?? '').toLowerCase().includes(q)
    ))
  }, [ebooks, filter])

  if (!token) {
    return (
      <main className="max-w-md mx-auto px-4 py-16 space-y-3">
        <h1 className="text-2xl font-bold">Admin Login</h1>
        <input className="w-full border rounded px-3 py-2" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" />
        <input className="w-full border rounded px-3 py-2" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" type="password" />
        <button className="px-4 py-2 rounded bg-blue-600 text-white" onClick={login}>Login</button>
        {error && <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700">{error}</div>}
      </main>
    )
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-10 space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">Admin</h1>
        <button className="px-3 py-1 rounded border" onClick={loadAll}>Refresh</button>
        <button
          className="px-3 py-1 rounded border"
          onClick={() => {
            localStorage.removeItem(TOKEN_KEY)
            setToken('')
          }}
        >
          Logout
        </button>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {status && (
        <p className="text-sm">
          Redis: {String(status.redis_ok)} · Celery: {String(status.celery_ok)} · Workers: {status.celery_workers}
        </p>
      )}
      {cacheStats && (
        <p className="text-sm">Cache keys: {cacheStats.keys} · Bytes: {cacheStats.total_bytes} · TTL: {cacheStats.ttl_seconds}s</p>
      )}
      <section className="space-y-2">
        <div className="flex gap-2">
          <button className={`px-3 py-1 rounded border ${tab === 'ebooks' ? 'bg-gray-100' : ''}`} onClick={() => setTab('ebooks')}>Stored ebooks</button>
          <button className={`px-3 py-1 rounded border ${tab === 'tasks' ? 'bg-gray-100' : ''}`} onClick={() => setTab('tasks')}>Tasks running</button>
          <button className={`px-3 py-1 rounded border ${tab === 'cache' ? 'bg-gray-100' : ''}`} onClick={() => setTab('cache')}>Cached pages</button>
        </div>
      </section>
      {tab === 'ebooks' ? (
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Stored ebooks</h2>
            <button
              className="text-xs text-red-600"
              onClick={async () => {
                if (!window.confirm('Delete ALL stored ebooks? This cannot be undone.')) return
                await adminDeleteAllEbooks(token)
                await loadAll()
              }}
            >
              Delete all stored ebooks
            </button>
          </div>
          <input
            className="w-full border rounded px-3 py-2 text-sm"
            placeholder="Filter by title or source URL…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <div className="space-y-2 text-sm">
            {filteredEbooks.map((e) => (
                <div key={e.job_id} className="border rounded p-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium">{e.ebook_title ?? e.job_id}</div>
                    <div className="flex items-center gap-2">
                      <button
                        className="text-xs text-blue-600 underline"
                        onClick={async () => {
                          try {
                            const res = await adminRegenerateEbook(token, e.job_id, true)
                            addJobToHistory(res.job_id, e.ebook_title ?? 'Generating ebook…', res.source_url || e.source_url)
                            await loadAll()
                            navigate('/history')
                          } catch (err: any) {
                            setError(err?.message ?? 'Regenerate (cache) failed')
                          }
                        }}
                      >
                        Regenerate (cache)
                      </button>
                      <button
                        className="text-xs text-orange-600 underline"
                        onClick={async () => {
                          if (!window.confirm('Regenerate from scratch (clear site cache first)?')) return
                          try {
                            const res = await adminRegenerateEbook(token, e.job_id, false)
                            addJobToHistory(res.job_id, e.ebook_title ?? 'Generating ebook…', res.source_url || e.source_url)
                            await loadAll()
                            navigate('/history')
                          } catch (err: any) {
                            setError(err?.message ?? 'Regenerate (from scratch) failed')
                          }
                        }}
                      >
                        Regenerate (from scratch)
                      </button>
                    </div>
                  </div>
                  <div className="text-xs text-gray-500">
                    <span className="align-middle">status=</span> <StatusBadge status={e.status} /> · posts={e.posts_count ?? '—'} · source={e.source_url ? <a className="text-blue-600 underline" href={e.source_url} target="_blank" rel="noreferrer">{e.source_url}</a> : '—'} · dir={e.dir_path}
                  </div>
                  <div className="text-xs text-gray-500 flex items-center gap-2 flex-wrap">
                    created={fmtDate(e.created_at)} · expires={fmtDate(e.expires_at)}
                    <span className={timeLeftMeta(e.expires_at).cls}>({timeLeftMeta(e.expires_at).text})</span>
                  </div>
                  <div className="flex gap-3 flex-wrap">
                    {e.files.map((f: any) => (
                      <a
                        key={f.path}
                        className="text-xs text-blue-600 underline"
                        href={`/api/jobs/${e.job_id}/download/${f.name.endsWith('.epub') ? 'epub' : f.name.endsWith('.mobi') ? 'mobi' : 'pdf'}`}
                      >
                        {f.name} ({f.size_bytes}b)
                      </a>
                    ))}
                  </div>
                  <button className="text-xs text-red-600" onClick={async () => { await adminDeleteEbook(token, e.job_id); await loadAll() }}>Delete ebook/work</button>
                </div>
              ))}
          </div>
        </section>
      ) : tab === 'tasks' ? (
        <section className="space-y-3">
          <h2 className="font-semibold">Tasks running</h2>
          <div className="text-xs text-gray-500">Running: {tasks.running.length} · Pending: {tasks.pending.length}</div>
          <div className="space-y-2 text-sm">
            {tasks.running.map((t) => (
              <div key={t.job_id} className="border rounded p-2">
                <div className="font-medium">{t.job_id}</div>
                <div className="text-xs text-gray-500">
                  status=<StatusBadge status={t.status} /> · progress={t.progress}% · elapsed={Math.floor(t.elapsed_seconds / 60)}m
                </div>
                <div className="text-xs text-gray-500">
                  cache posts={fmtCacheRatio(t.posts_cached ?? 0, (t.posts_crawled ?? 0) || (t.posts_found ?? 0))} ·
                  images={fmtCacheRatio(t.images_cached ?? 0, (t.images_embedded ?? 0) || (t.images_found ?? 0))}
                </div>
                {t.source_url && <a className="text-xs text-blue-600 underline" href={t.source_url} target="_blank" rel="noreferrer">{t.source_url}</a>}
                <div>
                  <button className="text-xs text-red-600" onClick={async () => { await adminKillTask(token, t.job_id); await loadAll() }}>Kill task</button>
                </div>
              </div>
            ))}
            {tasks.pending.map((t) => (
              <div key={t.job_id} className="border rounded p-2">
                <div className="font-medium">{t.job_id}</div>
                <div className="text-xs text-gray-500">
                  queue={t.queue_position} · status=<StatusBadge status={t.status} /> · elapsed={Math.floor(t.elapsed_seconds / 60)}m
                </div>
                {t.source_url && <a className="text-xs text-blue-600 underline" href={t.source_url} target="_blank" rel="noreferrer">{t.source_url}</a>}
                <div>
                  <button className="text-xs text-red-600" onClick={async () => { await adminKillTask(token, t.job_id); await loadAll() }}>Kill task</button>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : (
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Cached pages</h2>
            <button
              className="text-xs text-red-600"
              onClick={async () => {
                if (!window.confirm('Delete ALL cached pages? This cannot be undone.')) return
                await adminDeleteAllCache(token)
                await loadAll()
              }}
            >
              Delete all cache
            </button>
          </div>
          <div className="space-y-2 text-sm">
            {cacheSites.map((s) => (
              <div key={s.site} className="border rounded p-2">
                <div className="flex items-center justify-between gap-3">
                  <button className="font-medium underline" onClick={() => setOpenSite(openSite === s.site ? null : s.site)}>
                    {s.site}
                  </button>
                  <button
                    className="text-xs text-red-600"
                    onClick={async () => { await adminDeleteCacheSite(token, s.site); await loadAll() }}
                  >
                    Delete cache
                  </button>
                </div>
                <div className="text-xs text-gray-500">pages={s.pages_count} · images={s.images_count_total} · size={fmtBytes(s.total_bytes)}</div>
                {openSite === s.site && (
                  <div className="mt-2 space-y-1">
                    {s.pages.map((c: any) => (
                      <div key={c.key} className="border rounded p-2">
                        <a className="truncate text-blue-600 underline block" href={c.url} target="_blank" rel="noreferrer">{c.url}</a>
                        <div className="text-xs text-gray-500">
                          {c.key} · ttl={c.ttl_seconds}s · {c.size_bytes} bytes · imgs={c.image_count}
                        </div>
                        <button className="text-xs text-red-600" onClick={async () => { await adminDeleteCacheEntry(token, c.key); await loadAll() }}>Delete cache</button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  )
}
