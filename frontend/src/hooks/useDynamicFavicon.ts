import { useEffect, useRef } from 'react'
import type { JobStatus } from '@/types/job'

const ORIGINAL_HREF = '/favicon.svg'
const ORIGINAL_TYPE = 'image/svg+xml'
const SIZE = 64

function _draw(status: JobStatus, progress: number): string {
  const canvas = document.createElement('canvas')
  canvas.width = SIZE
  canvas.height = SIZE
  const ctx = canvas.getContext('2d')!

  const cx = SIZE / 2
  const cy = SIZE / 2
  const r = SIZE / 2 - 5

  // Dark background disc
  ctx.beginPath()
  ctx.arc(cx, cy, SIZE / 2, 0, Math.PI * 2)
  ctx.fillStyle = '#0f0f1a'
  ctx.fill()

  if (status === 'done') {
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.strokeStyle = '#22c55e'
    ctx.lineWidth = 6
    ctx.stroke()
    ctx.strokeStyle = '#22c55e'
    ctx.lineWidth = 5
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.beginPath()
    ctx.moveTo(cx - 11, cy + 1)
    ctx.lineTo(cx - 2, cy + 10)
    ctx.lineTo(cx + 12, cy - 9)
    ctx.stroke()
    return canvas.toDataURL()
  }

  if (status === 'error') {
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.strokeStyle = '#ef4444'
    ctx.lineWidth = 6
    ctx.stroke()
    ctx.strokeStyle = '#ef4444'
    ctx.lineWidth = 5
    ctx.lineCap = 'round'
    ctx.beginPath()
    ctx.moveTo(cx - 9, cy - 9); ctx.lineTo(cx + 9, cy + 9)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(cx + 9, cy - 9); ctx.lineTo(cx - 9, cy + 9)
    ctx.stroke()
    return canvas.toDataURL()
  }

  if (status === 'queued') {
    ctx.setLineDash([5, 5])
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.strokeStyle = '#6b7280'
    ctx.lineWidth = 6
    ctx.stroke()
    ctx.setLineDash([])
    ctx.fillStyle = '#9ca3af'
    ctx.font = 'bold 14px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('…', cx, cy + 1)
    return canvas.toDataURL()
  }

  // Active progress states
  const pct = Math.round(Math.max(0, Math.min(100, progress)))

  // Background ring
  ctx.beginPath()
  ctx.arc(cx, cy, r, 0, Math.PI * 2)
  ctx.strokeStyle = '#2d2d44'
  ctx.lineWidth = 7
  ctx.stroke()

  // Progress arc (starts at top)
  if (pct > 0) {
    const start = -Math.PI / 2
    const end = start + Math.PI * 2 * (pct / 100)
    ctx.beginPath()
    ctx.arc(cx, cy, r, start, end)
    ctx.strokeStyle = '#863bff'
    ctx.lineWidth = 7
    ctx.lineCap = 'round'
    ctx.stroke()
  }

  // Percentage number
  ctx.fillStyle = '#ffffff'
  const fontSize = pct >= 100 ? 15 : pct >= 10 ? 17 : 19
  ctx.font = `bold ${fontSize}px sans-serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(`${pct}`, cx, cy + 1)

  return canvas.toDataURL()
}

export function useDynamicFavicon(status: JobStatus | null, progress: number) {
  const linkRef = useRef<HTMLLinkElement | null>(null)

  useEffect(() => {
    let link = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
    if (!link) {
      link = document.createElement('link')
      link.rel = 'icon'
      document.head.appendChild(link)
    }
    linkRef.current = link

    return () => {
      if (linkRef.current) {
        linkRef.current.type = ORIGINAL_TYPE
        linkRef.current.href = ORIGINAL_HREF
      }
    }
  }, [])

  useEffect(() => {
    const link = linkRef.current
    if (!link || !status) return
    link.type = 'image/png'
    link.href = _draw(status, progress)
  }, [status, progress])
}
