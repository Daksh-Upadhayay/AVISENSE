import { useState } from 'react'
import { COLORS, formatRul } from '../../lib/format'

const SHOWN = 7

/**
 * SHAP waterfall: how each sensor moved this engine's estimate away from the
 * average engine. Bars are exact TreeSHAP contributions, in cycles.
 */
export function Waterfall({ explanation, rul, cap = 125 }) {
  const [hover, setHover] = useState(null)
  const { base_rul: base, raw_rul: raw, contributions } = explanation
  const top = contributions.slice(0, SHOWN)
  const rest = contributions.slice(SHOWN)
  const restTotal = rest.reduce((s, c) => s + c.cycles, 0)
  const items = [...top]
  if (rest.length) items.push({ feature: 'other', symbol: 'Other', label: `${rest.length} other inputs`, cycles: restTotal })

  // Cumulative path from base to raw output, most important first.
  let running = base
  const steps = items.map((c) => {
    const start = running
    running += c.cycles
    return { ...c, start, end: running }
  })
  // Zoom to the range the bars actually cover, so small contributions stay visible.
  const values = [base, raw, ...steps.flatMap((s) => [s.start, s.end])]
  const pad = Math.max(2, (Math.max(...values) - Math.min(...values)) * 0.08)
  const lo = Math.min(...values) - pad
  const hi = Math.max(...values) + pad
  const x = (v) => ((v - lo) / (hi - lo)) * 100

  const describe = (s) =>
    s.cycles < 0
      ? `${s.label} shortens the estimate by ${Math.abs(s.cycles).toFixed(1)} cycles`
      : `${s.label} extends the estimate by ${s.cycles.toFixed(1)} cycles`

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-4 text-xs text-ink-secondary" aria-hidden>
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-sm" style={{ background: COLORS.shortens }} /> Shortens life
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-sm" style={{ background: COLORS.extends }} /> Extends life
        </span>
      </div>
      <table className="w-full text-sm">
        <caption className="sr-only">Contribution of each input to the remaining-life estimate, in cycles</caption>
        <tbody>
          <Row label="Average engine" sub="model baseline" value={`${base.toFixed(0)}`}>
            <Marker left={x(base)} />
          </Row>
          {steps.map((s) => (
            <Row
              key={s.feature}
              label={s.symbol}
              sub={s.label}
              value={`${s.cycles > 0 ? '+' : ''}${s.cycles.toFixed(1)}`}
              onHover={() => setHover(s)}
              onLeave={() => setHover(null)}
            >
              <div
                className="absolute top-1/2 h-3 -translate-y-1/2 rounded-sm"
                style={{
                  left: `${x(Math.min(s.start, s.end))}%`,
                  width: `max(2px, ${Math.abs(x(s.end) - x(s.start))}%)`,
                  background: s.cycles < 0 ? COLORS.shortens : COLORS.extends,
                }}
              />
            </Row>
          ))}
          <Row label="This engine" sub={raw > cap ? `model output ${raw.toFixed(0)}, capped at ${cap}` : 'estimated RUL'} value={formatRul(rul, cap)} strong>
            <Marker left={x(raw)} strong />
          </Row>
        </tbody>
      </table>
      <p className="mt-3 min-h-5 text-xs text-ink-muted" aria-live="polite">
        {hover ? describe(hover) : 'Hover a bar for details. Bars add up from the average engine to this engine.'}
      </p>
    </div>
  )
}

function Row({ label, sub, value, strong, children, onHover, onLeave }) {
  return (
    <tr className="group" onMouseEnter={onHover} onMouseLeave={onLeave}>
      <th scope="row" className="w-32 py-1.5 pr-3 text-left align-middle font-normal">
        <div className={strong ? 'font-semibold text-ink' : 'font-medium text-ink'}>{label}</div>
        <div className="truncate text-xs text-ink-muted" title={sub}>
          {sub}
        </div>
      </th>
      <td className="py-1.5">
        <div className="relative h-7 rounded group-hover:bg-surface-hover">{children}</div>
      </td>
      <td className={`w-14 py-1.5 pl-3 text-right tabular ${strong ? 'font-semibold text-ink' : 'text-ink-secondary'}`}>{value}</td>
    </tr>
  )
}

function Marker({ left, strong }) {
  return (
    <div
      className="absolute top-1/2 h-5 w-0.5 -translate-y-1/2 rounded"
      style={{ left: `${left}%`, background: strong ? COLORS.ink : COLORS.muted }}
    />
  )
}
