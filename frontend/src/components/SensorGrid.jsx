import { useState } from 'react'
import { COLORS, SENSOR_STATE } from '../lib/format'

const W = 240
const H = 64

/** Drift of one sensor over the recorded cycles, against its noise band and typical failure level. */
function Sparkline({ sensor, cycles }) {
  const [hover, setHover] = useState(null)
  const series = sensor.series
  const extent = Math.max(sensor.failure_level * 1.25, ...series.map(Math.abs), 1)
  const y = (v) => H / 2 - (v / extent) * (H / 2 - 4)
  const x = (i) => (series.length === 1 ? W / 2 : (i / (series.length - 1)) * W)
  const path = series.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const fail = sensor.typical_direction === 'up' ? sensor.failure_level : -sensor.failure_level

  const onMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const i = Math.round(((e.clientX - rect.left) / rect.width) * (series.length - 1))
    setHover(Math.max(0, Math.min(series.length - 1, i)))
  }

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="h-16 w-full"
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        role="img"
        aria-label={`${sensor.symbol} drift over time, currently ${sensor.drift} standard deviations`}
      >
        <rect x="0" y={y(sensor.noise_level)} width={W} height={y(-sensor.noise_level) - y(sensor.noise_level)} fill={COLORS.ink2} opacity="0.08" />
        <line x1="0" x2={W} y1={y(0)} y2={y(0)} stroke={COLORS.grid} vectorEffect="non-scaling-stroke" />
        <line x1="0" x2={W} y1={y(fail)} y2={y(fail)} stroke={COLORS.critical} strokeOpacity="0.7" vectorEffect="non-scaling-stroke" />
        <path d={path} fill="none" stroke={COLORS.predicted} strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
        {hover != null && (
          <line x1={x(hover)} x2={x(hover)} y1="0" y2={H} stroke={COLORS.muted} vectorEffect="non-scaling-stroke" />
        )}
      </svg>
      {hover != null && (
        <div className="pointer-events-none absolute -top-8 right-0 rounded border border-line-strong bg-surface-raised px-2 py-1 text-xs text-ink-secondary">
          Cycle {cycles[hover]}: <span className="text-ink tabular">{series[hover] > 0 ? '+' : ''}{series[hover].toFixed(2)}σ</span>
        </div>
      )}
    </div>
  )
}

export function SensorGrid({ sensors, cycles }) {
  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-4 text-xs text-ink-secondary" aria-hidden>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded" style={{ background: COLORS.predicted }} /> Drift from this engine's start (σ)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-4 rounded-sm" style={{ background: COLORS.ink2, opacity: 0.2 }} /> Normal noise
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded" style={{ background: COLORS.critical }} /> Typical level 10 cycles before failure
        </span>
      </div>
      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {sensors.map((s) => {
          const state = SENSOR_STATE[s.state]
          const Icon = state.icon
          return (
            <li key={s.sensor} className="rounded-lg border border-line bg-page p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-medium text-ink">
                    {s.symbol} <span className="font-normal text-ink-muted">· {s.name}</span>
                  </div>
                  <div className="text-xs text-ink-muted">
                    {s.subsystem} · now {formatValue(s.value)} {s.unit}
                  </div>
                </div>
                <span className="flex shrink-0 items-center gap-1 text-xs text-ink-secondary">
                  <Icon className="h-3.5 w-3.5" style={{ color: state.color }} aria-hidden />
                  {state.label}
                </span>
              </div>
              <div className="mt-2">
                <Sparkline sensor={s} cycles={cycles} />
              </div>
              <div className="mt-2 flex items-center gap-2">
                <div className="h-1.5 flex-1 rounded-full bg-surface-hover" title="Share of the way from normal noise to typical failure-level drift">
                  <div className="h-full rounded-full" style={{ width: `${Math.min(100, s.progress * 100)}%`, background: state.color }} />
                </div>
                <span className="w-24 text-right text-xs text-ink-secondary tabular">
                  {s.drift > 0 ? '+' : ''}
                  {s.drift.toFixed(1)}σ · {s.progress >= 1 ? 'past' : `${Math.round(s.progress * 100)}%`}
                </span>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function formatValue(v) {
  const abs = Math.abs(v)
  if (abs >= 1000) return v.toFixed(0)
  if (abs >= 100) return v.toFixed(1)
  if (abs >= 1) return v.toFixed(2)
  return v.toFixed(4)
}
