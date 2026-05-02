import type { BasicJobRequest, AdvancedJobRequest } from '@/types/ebook'
import type { JobStatusResponse } from '@/types/job'
import type { SystemStatusResponse } from '@/types/system'
import type { HealthResponse } from '@/types/health'

const BASE = import.meta.env.VITE_API_URL ?? ''

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(text)
  }
  return res.json() as Promise<T>
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
