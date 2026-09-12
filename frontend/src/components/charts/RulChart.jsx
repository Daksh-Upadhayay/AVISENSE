import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { COLORS, formatProbability, formatRul } from '../../lib/format'

const axis = { stroke: COLORS.axis, tick: { fill: COLORS.muted, fontSize: 12 }, tickLine: false }

function RulTooltip({ active, payload, cap }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-md border border-line-strong bg-surface-raised px-3 py-2 text-xs text-ink-secondary shadow-lg">
      <div className="mb-1 font-medium text-ink">Cycle {d.cycle}</div>
      <Row color={COLORS.predicted} label="Predicted" value={`${formatRul(d.rul, cap)} cycles`} />
      <div className="pl-4 text-ink-muted">
        80% range {Math.round(d.rul_low)}–{formatRul(d.rul_high, cap)}
      </div>
      {d.true_rul != null && <Row color={COLORS.actual} label="Actual" value={`${d.true_rul} cycles`} />}
      <div className="mt-1 text-ink-muted">Failure within 30 cycles: {formatProbability(d.failure_probability)}</div>
    </div>
  )
}

function Row({ color, label, value }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-0.5 w-3 rounded" style={{ background: color }} />
      <span>{label}</span>
      <span className="ml-auto pl-3 font-medium text-ink tabular">{value}</span>
    </div>
  )
}

/** Predicted RUL over the engine's recorded cycles, with its calibrated range and, for replays, the truth. */
export function RulChart({ trajectory, cap = 125 }) {
  const hasTruth = trajectory.some((d) => d.true_rul != null)
  const data = trajectory.map((d) => ({
    ...d,
    band: [d.rul_low, d.rul_high],
    actual: d.true_rul != null ? Math.min(d.true_rul, cap) : null,
  }))
  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-4 text-xs text-ink-secondary" aria-hidden>
        <Legend swatch={<span className="h-0.5 w-4 rounded" style={{ background: COLORS.predicted }} />} label="Predicted RUL" />
        <Legend swatch={<span className="h-3 w-4 rounded-sm" style={{ background: COLORS.predicted, opacity: 0.18 }} />} label="80% range" />
        {hasTruth && <Legend swatch={<span className="h-0.5 w-4 rounded" style={{ background: COLORS.actual }} />} label={`Actual RUL (capped at ${cap})`} />}
      </div>
      <div className="h-72" role="img" aria-label="Remaining useful life by cycle">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
            <CartesianGrid stroke={COLORS.grid} vertical={false} />
            <XAxis dataKey="cycle" type="number" domain={['dataMin', 'dataMax']} {...axis} tickCount={8} allowDecimals={false} />
            <YAxis domain={[0, cap + 5]} ticks={[0, 25, 50, 75, 100, cap]} {...axis} width={44} />
            <ReferenceLine y={30} stroke={COLORS.axis} label={{ value: '30-cycle window', position: 'insideTopRight', fill: COLORS.muted, fontSize: 11 }} />
            <Tooltip content={<RulTooltip cap={cap} />} cursor={{ stroke: COLORS.muted, strokeWidth: 1 }} />
            <Area dataKey="band" stroke="none" fill={COLORS.predicted} fillOpacity={0.18} isAnimationActive={false} activeDot={false} />
            {hasTruth && (
              <Line dataKey="actual" stroke={COLORS.actual} strokeWidth={2} dot={false} isAnimationActive={false} activeDot={false} />
            )}
            <Line
              dataKey="rul"
              stroke={COLORS.predicted}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
              activeDot={{ r: 4, stroke: COLORS.surface, strokeWidth: 2 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

/** Probability of failure within the horizon, by cycle, against the alert threshold. */
export function RiskChart({ trajectory, threshold, horizon = 30 }) {
  return (
    <div className="h-44" role="img" aria-label={`Probability of failure within ${horizon} cycles, by cycle`}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={trajectory} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
          <CartesianGrid stroke={COLORS.grid} vertical={false} />
          <XAxis dataKey="cycle" type="number" domain={['dataMin', 'dataMax']} {...axis} tickCount={8} allowDecimals={false} />
          <YAxis domain={[0, 1]} ticks={[0, 0.5, 1]} tickFormatter={(v) => `${v * 100}%`} {...axis} width={44} />
          <ReferenceLine
            y={threshold}
            stroke={COLORS.critical}
            strokeOpacity={0.7}
            label={{ value: 'Critical above this', position: 'insideTopRight', fill: COLORS.muted, fontSize: 11 }}
          />
          <Tooltip
            cursor={{ stroke: COLORS.muted, strokeWidth: 1 }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className="rounded-md border border-line-strong bg-surface-raised px-3 py-2 text-xs text-ink-secondary shadow-lg">
                  <div className="font-medium text-ink">Cycle {payload[0].payload.cycle}</div>
                  Failure within {horizon} cycles: <span className="font-medium text-ink">{formatProbability(payload[0].payload.failure_probability)}</span>
                </div>
              ) : null
            }
          />
          <Area
            dataKey="failure_probability"
            stroke={COLORS.predicted}
            strokeWidth={2}
            fill={COLORS.predicted}
            fillOpacity={0.1}
            isAnimationActive={false}
            activeDot={{ r: 4, stroke: COLORS.surface, strokeWidth: 2 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

function Legend({ swatch, label }) {
  return (
    <span className="flex items-center gap-1.5">
      {swatch}
      {label}
    </span>
  )
}
