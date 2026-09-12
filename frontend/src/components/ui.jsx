import { useEffect, useId } from 'react'
import { createPortal } from 'react-dom'
import { Info, Loader2, X } from 'lucide-react'
import { STATUS } from '../lib/format'

export function Button({ variant = 'primary', size = 'md', loading = false, className = '', children, ...props }) {
  const variants = {
    primary: 'bg-accent-strong text-white hover:bg-accent',
    secondary: 'bg-surface-raised text-ink border border-line-strong hover:bg-surface-hover',
    ghost: 'text-ink-secondary hover:text-ink hover:bg-surface-hover',
    danger: 'text-shorten border border-line-strong hover:bg-critical/15',
  }
  const sizes = { sm: 'h-8 px-3 text-sm', md: 'h-10 px-4 text-sm' }
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
      disabled={loading || props.disabled}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  )
}

export function Card({ className = '', children, ...props }) {
  return (
    <section className={`rounded-lg border border-line bg-surface p-5 ${className}`} {...props}>
      {children}
    </section>
  )
}

export function SectionTitle({ title, hint, action }) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold text-ink">{title}</h2>
        {hint && <p className="mt-1 max-w-2xl text-sm text-ink-muted">{hint}</p>}
      </div>
      {action}
    </div>
  )
}

export function StatusBadge({ status, size = 'md' }) {
  const meta = STATUS[status]
  if (!meta) return <span className="text-sm text-ink-muted">Not assessed</span>
  const Icon = meta.icon
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border border-line-strong bg-surface-raised font-medium text-ink ${size === 'lg' ? 'px-3 py-1 text-sm' : 'px-2 py-0.5 text-xs'}`}
    >
      <Icon className={size === 'lg' ? 'h-4 w-4' : 'h-3.5 w-3.5'} style={{ color: meta.color }} aria-hidden />
      {meta.label}
    </span>
  )
}

export function Spinner({ label = 'Loading' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-ink-muted" role="status">
      <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
      {label}
    </div>
  )
}

export function ErrorNote({ error, className = '' }) {
  if (!error) return null
  return (
    <div role="alert" className={`rounded-md border border-critical/40 bg-critical/10 px-3 py-2 text-sm text-ink ${className}`}>
      {error.message || String(error)}
    </div>
  )
}

export function Note({ children }) {
  return (
    <div className="flex gap-2 rounded-md border border-line bg-surface-raised px-3 py-2 text-sm text-ink-secondary">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-ink-muted" aria-hidden />
      <div>{children}</div>
    </div>
  )
}

export function Field({ label, hint, children }) {
  const id = useId()
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-ink-secondary">
        {label}
      </label>
      {children(id)}
      {hint && <p className="text-xs text-ink-muted">{hint}</p>}
    </div>
  )
}

export const inputClass =
  'h-10 w-full rounded-md border border-line-strong bg-page px-3 text-sm text-ink placeholder:text-ink-muted focus:border-accent focus:outline-none'

export function Modal({ open, onClose, title, children, width = 'max-w-lg' }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`w-full ${width} rounded-lg border border-line-strong bg-surface shadow-2xl`}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 className="text-base font-semibold text-ink">{title}</h2>
          <button onClick={onClose} className="rounded p-1 text-ink-muted hover:bg-surface-hover hover:text-ink" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>,
    document.body,
  )
}

export function Stat({ label, value, sub, children }) {
  return (
    <div className="rounded-lg border border-line bg-surface px-4 py-3">
      <div className="text-sm text-ink-muted">{label}</div>
      <div className="mt-1 flex items-baseline gap-2 text-2xl font-semibold text-ink">
        {value}
        {children}
      </div>
      {sub && <div className="mt-0.5 text-xs text-ink-muted">{sub}</div>}
    </div>
  )
}
