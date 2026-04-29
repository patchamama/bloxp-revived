const STORAGE_KEY = 'bloxp_job_history'
const MAX_HISTORY = 50

export interface HistoryEntry {
  job_id: string
  title: string
  created_at: number // unix ms
}

function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as HistoryEntry[]) : []
  } catch {
    return []
  }
}

function saveHistory(entries: HistoryEntry[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
}

export function addJobToHistory(job_id: string, title: string): void {
  const entries = loadHistory()
  const filtered = entries.filter((e) => e.job_id !== job_id)
  const updated = [{ job_id, title, created_at: Date.now() }, ...filtered].slice(0, MAX_HISTORY)
  saveHistory(updated)
}

export function removeJobFromHistory(job_id: string): void {
  const entries = loadHistory().filter((e) => e.job_id !== job_id)
  saveHistory(entries)
}

export function getJobHistory(): HistoryEntry[] {
  return loadHistory()
}
