import { CircleCheck, OctagonAlert, TriangleAlert } from 'lucide-react'

// Chart colors (dark mode steps of the validated reference palette).
export const COLORS = {
  surface: '#1a1a19',
  grid: '#2c2c2a',
  axis: '#383835',
  ink: '#ffffff',
  ink2: '#c3c2b7',
  muted: '#898781',
  predicted: '#3987e5',
  actual: '#c3c2b7',
  extends: '#3987e5',
  shortens: '#e66767',
  good: '#0ca30c',
  warning: '#fab219',
  critical: '#d03b3b',
}

export const STATUS = {
  healthy: { label: 'Healthy', color: COLORS.good, icon: CircleCheck, rank: 2 },
  watch: { label: 'Watch', color: COLORS.warning, icon: TriangleAlert, rank: 1 },
  critical: { label: 'Critical', color: COLORS.critical, icon: OctagonAlert, rank: 0 },
}

export const SENSOR_STATE = {
  normal: { label: 'Normal', color: COLORS.good, icon: CircleCheck },
  elevated: { label: 'Elevated', color: COLORS.warning, icon: TriangleAlert },
  alert: { label: 'At failure level', color: COLORS.critical, icon: OctagonAlert },
}

export function formatRul(value, cap = 125) {
  if (value == null) return '—'
  return value >= cap - 0.5 ? `${cap}+` : Math.round(value).toString()
}

export function formatProbability(p) {
  if (p == null) return '—'
  if (p < 0.01) return '<1%'
  if (p > 0.99) return '>99%'
  return `${Math.round(p * 100)}%`
}

export function formatDate(iso) {
  if (!iso) return '—'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso))
}

export function relativeTime(iso) {
  if (!iso) return '—'
  const seconds = (Date.now() - new Date(iso).getTime()) / 1000
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
  if (seconds < 60) return rtf.format(-Math.round(seconds), 'second')
  if (seconds < 3600) return rtf.format(-Math.round(seconds / 60), 'minute')
  if (seconds < 86400) return rtf.format(-Math.round(seconds / 3600), 'hour')
  return rtf.format(-Math.round(seconds / 86400), 'day')
}

export function replayOf(engine) {
  return engine?.metadata?.replay ?? null
}
