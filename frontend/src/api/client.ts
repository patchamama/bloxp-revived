import type { BasicJobRequest, AdvancedJobRequest } from '@/types/ebook'
import type { JobStatusResponse } from '@/types/job'
import type { SystemStatusResponse } from '@/types/system'
import type { HealthResponse } from '@/types/health'

const BASE = import.meta.env.VITE_API_URL ?? import.meta.env.BASE_URL.replace(/\/$/, '')

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(text)
  }
  if (res.status === 204) {
    return undefined as T
  }
  const text = await res.text()
  if (!text) {
    return undefined as T
  }
  return JSON.parse(text) as T
}

export function submitBasicJob(data: BasicJobRequest): Promise<{ job_id: string }> {
  return apiFetch('/api/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: 'basic', ...data }),
  })
}

export function submitAdvancedJob(data: AdvancedJobRequest): Promise<{ job_id: string }> {
  return apiFetch('/api/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: 'advanced', ...data }),
  })
}

export function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return apiFetch(`/api/jobs/${jobId}`)
}

export async function cancelJob(jobId: string): Promise<void> {
  const res = await fetch(`${BASE}/api/jobs/${jobId}`, { method: 'DELETE' })
  if (!res.ok && res.status !== 404) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(text)
  }
}

export function getSystemStatus(): Promise<SystemStatusResponse> {
  return apiFetch('/api/system/status')
}

export function getHealth(): Promise<HealthResponse> {
  return apiFetch('/api/health')
}

function adminFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  return apiFetch(path, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
  })
}

export function adminLogin(username: string, password: string): Promise<{ token: string }> {
  return apiFetch('/api/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
}

export function adminStatus(token: string): Promise<{ redis_ok: boolean; celery_ok: boolean; celery_workers: number }> {
  return adminFetch('/api/admin/status', token)
}

export function adminCacheStats(token: string): Promise<{ keys: number; total_bytes: number; ttl_seconds: number }> {
  return adminFetch('/api/admin/cache/stats', token)
}

export function adminCacheEntries(
  token: string,
  page = 1,
  pageSize = 50,
): Promise<{ total: number; page: number; page_size: number; items: Array<{ key: string; url: string; ttl_seconds: number; size_bytes: number }> }> {
  return adminFetch(`/api/admin/cache/entries?page=${page}&page_size=${pageSize}`, token)
}

export function adminCacheSites(
  token: string,
): Promise<{ items: Array<{ site: string; pages_count: number; images_count_total: number; total_bytes: number; pages: Array<{ key: string; url: string; ttl_seconds: number; size_bytes: number; image_count: number }> }> }> {
  return adminFetch('/api/admin/cache/sites', token)
}

export async function adminDeleteCacheEntry(token: string, key: string): Promise<void> {
  await adminFetch(`/api/admin/cache/entries/${encodeURIComponent(key)}`, token, { method: 'DELETE' })
}

export async function adminDeleteCacheSite(token: string, site: string): Promise<void> {
  await adminFetch(`/api/admin/cache/sites/${encodeURIComponent(site)}`, token, { method: 'DELETE' })
}

export async function adminDeleteAllCache(token: string): Promise<void> {
  await adminFetch('/api/admin/cache/all', token, { method: 'DELETE' })
}

export function adminEbooks(token: string): Promise<{ items: Array<{ job_id: string; created_at: number | null; expires_at: number | null; status: string | null; ebook_title: string | null; source_url: string | null; dir_path: string; files: Array<{ name: string; path: string; size_bytes: number }> }> }> {
  return adminFetch('/api/admin/ebooks', token)
}

export async function adminDeleteEbook(token: string, jobId: string): Promise<void> {
  await adminFetch(`/api/admin/ebooks/${jobId}`, token, { method: 'DELETE' })
}

export async function adminDeleteAllEbooks(token: string): Promise<void> {
  await adminFetch('/api/admin/ebooks/all', token, { method: 'DELETE' })
}

export function adminRegenerateEbook(
  token: string,
  jobId: string,
  useCache: boolean,
): Promise<{ job_id: string; source_url: string; use_cache: boolean }> {
  return adminFetch(`/api/admin/ebooks/${jobId}/regenerate`, token, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ use_cache: useCache }),
  })
}

export function adminForceStartJob(token: string, jobId: string): Promise<{ ok: boolean; job_id: string }> {
  return adminFetch(`/api/admin/jobs/${jobId}/force-start`, token, {
    method: 'POST',
  })
}

export function adminTasks(
  token: string,
): Promise<{
  running: Array<{
    job_id: string
    status: string
    source_url?: string
    created_at: number
    elapsed_seconds: number
    progress: number
    posts_crawled: number
    posts_cached: number
    posts_found: number
    images_embedded: number
    images_cached: number
    images_found: number
  }>
  pending: Array<{ job_id: string; status: string; source_url?: string; created_at: number; elapsed_seconds: number; queue_position: number }>
}> {
  return adminFetch('/api/admin/tasks', token)
}

export function adminKillTask(token: string, jobId: string): Promise<{ ok: boolean; job_id: string }> {
  return adminFetch(`/api/admin/tasks/${jobId}/kill`, token, { method: 'POST' })
}
