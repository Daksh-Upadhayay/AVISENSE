import { useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ErrorBar, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import { api, useApi } from '../lib/api'
import { COLORS, formatDate } from '../lib/format'
import { Layout } from '../components/Layout'
import { Card, ErrorNote, SectionTitle, Spinner, Stat } from '../components/ui'

const axis = { stroke: COLORS.axis, tick: { fill: COLORS.muted, fontSize: 12 }, tickLine: false }
const ALGORITHM_LABELS = {
  rul: 'Remaining useful life',
  interval: 'Uncertainty range',
  failure: 'Failure probability',
  explanations: 'Explanations',
}
const tooltipBox = 'rounded-md border border-line-strong bg-surface-raised px-3 py-2 text-xs text-ink-secondary shadow-lg'

export default function ModelCard() {
  const card = useApi(() => api.model(), [])
  return (
    <Layout>
      {card.loading ? <Spinner label="Loading model card" /> : card.error ? <ErrorNote error={card.error} /> : <Content card={card.data} />}
    </Layout>
  )
}

function pct(v) {
  return `${Math.round(v * 100)}%`
}

function Content({ card }) {
  const m = card.metrics
  const o = m.overall
  const prev = m.previous_release
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Model card</h1>
        <p className="mt-1 max-w-3xl text-sm text-ink-muted">
          Version {card.version}, trained {formatDate(card.trained_at)}. Every number below comes from NASA's official C-MAPSS test engines,
          which the model never saw in training. Error is in engine cycles.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="RUL error (RMSE)" value={o.rmse.toFixed(2)} sub={`cycles, ${o.engines} test engines`} />
        <Stat label="Range coverage" value={pct(o.interval_coverage)} sub={`of true values inside the 80% range (avg width ${o.interval_width})`} />
        <Stat label="Failures caught" value={pct(o.recall)} sub="of cycles within 30 of failure flagged critical" />
        <Stat label="Alert precision" value={pct(o.precision)} sub="of critical flags that were real" />
      </div>

      <Card className="overflow-x-auto">
        <SectionTitle
          title="Results by test set"
          hint="FD002 and FD004 mix six flight conditions; FD003 and FD004 add a second fault mode. One model covers all four."
        />
        <table className="w-full min-w-[720px] text-sm tabular">
          <thead>
            <tr className="border-b border-line text-left text-xs text-ink-muted">
              <th className="py-2 pr-3 font-medium">Test set</th>
              <th className="px-3 py-2 text-right font-medium">Engines</th>
              <th className="px-3 py-2 text-right font-medium">RMSE</th>
              <th className="px-3 py-2 text-right font-medium">MAE</th>
              <th className="px-3 py-2 text-right font-medium">NASA score</th>
              <th className="px-3 py-2 text-right font-medium">Range coverage</th>
              <th className="px-3 py-2 text-right font-medium">PR-AUC</th>
              <th className="px-3 py-2 text-right font-medium">Recall</th>
              <th className="py-2 pl-3 text-right font-medium">Precision</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(m.per_dataset).map(([name, d]) => (
              <tr key={name} className="border-b border-line text-ink-secondary last:border-0">
                <td className="py-2 pr-3 text-ink">
                  {name} <span className="text-xs text-ink-muted">· {card.training_data.subsets[name].conditions} condition(s), {card.training_data.subsets[name].fault_modes}</span>
                </td>
                <td className="px-3 py-2 text-right">{d.engines}</td>
                <td className="px-3 py-2 text-right text-ink">{d.rmse.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{d.mae.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{Math.round(d.nasa_score)}</td>
                <td className="px-3 py-2 text-right">{pct(d.interval_coverage)}</td>
                <td className="px-3 py-2 text-right">{d.pr_auc.toFixed(3)}</td>
                <td className="px-3 py-2 text-right">{pct(d.recall)}</td>
                <td className="py-2 pl-3 text-right">{pct(d.precision)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {prev && (
          <p className="mt-4 text-sm text-ink-muted">
            Previous release ({prev.name}): FD001 RMSE {prev.fd001_rmse_as_served} as the old API served it, {prev.fd001_rmse_with_history} when given
            real history. {prev.note}
          </p>
        )}
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <SectionTitle
            title="Predicted vs actual RUL"
            hint="One point per test engine at its last recorded cycle, with its 80% range. Points on the diagonal are exact. Truth is capped at 125, the model's horizon."
          />
          <PredictedVsActual points={m.test_scatter} />
        </Card>
        <Card>
          <SectionTitle
            title="Error by distance from failure"
            hint="Mean absolute error over every test cycle, grouped by the true RUL. Accuracy is highest where it matters: close to failure."
          />
          <ErrorByBand bands={m.error_by_rul} />
        </Card>
        <Card>
          <SectionTitle
            title="Is the failure probability honest?"
            hint="Test cycles grouped by predicted probability. On the diagonal, a predicted 70% means failure within 30 cycles happened 70% of the time."
          />
          <Reliability bins={m.reliability} />
        </Card>
        <Card>
          <SectionTitle title="What the model relies on" hint="Average absolute SHAP contribution per input across test cycles, in cycles of RUL." />
          <Importance items={m.global_importance} sensors={card.features.sensors} />
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionTitle title="How it works" />
          <dl className="space-y-3 text-sm">
            {Object.entries(card.algorithm).map(([k, v]) => (
              <div key={k}>
                <dt className="font-medium text-ink">{ALGORITHM_LABELS[k] ?? k}</dt>
                <dd className="text-ink-secondary">{v}</dd>
              </div>
            ))}
            <div>
              <dt className="font-medium text-ink">Features ({card.features.count})</dt>
              <dd className="text-ink-secondary">{card.features.description}</dd>
            </div>
            <div>
              <dt className="font-medium text-ink">Status rules</dt>
              <dd className="text-ink-secondary">
                Critical when P(failure within {card.policy.horizon} cycles) ≥ {pct(card.policy.alert_threshold)}. Watch when the low end of the RUL
                range is {card.policy.watch_rul} cycles or less. Healthy otherwise. The threshold was set on held-out training engines to catch 95% of
                failures there.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-ink">Training data</dt>
              <dd className="text-ink-secondary">
                {card.training_data.source}. {card.training_data.fit_engines} engines for fitting, {card.training_data.validation_engines} held out for
                calibration.
              </dd>
            </div>
          </dl>
        </Card>
        <Card>
          <SectionTitle title="Limitations" />
          <ul className="list-disc space-y-2 pl-5 text-sm text-ink-secondary">
            {card.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  )
}

function PredictedVsActual({ points }) {
  const [dataset, setDataset] = useState('All')
  const shown = useMemo(
    () =>
      points
        .filter((p) => dataset === 'All' || p.dataset === dataset)
        .map((p) => ({ ...p, err: [p.predicted - p.low, p.high - p.predicted] })),
    [points, dataset],
  )
  return (
    <div>
      <div className="mb-3 flex gap-1" role="group" aria-label="Test set">
        {['All', 'FD001', 'FD002', 'FD003', 'FD004'].map((d) => (
          <button
            key={d}
            onClick={() => setDataset(d)}
            className={`rounded-md px-2.5 py-1 text-xs ${dataset === d ? 'bg-surface-hover text-ink' : 'text-ink-muted hover:text-ink'}`}
            aria-pressed={dataset === d}
          >
            {d}
          </button>
        ))}
      </div>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 12, bottom: 16, left: 0 }}>
            <CartesianGrid stroke={COLORS.grid} />
            <XAxis type="number" dataKey="true" name="Actual" domain={[0, 130]} ticks={[0, 25, 50, 75, 100, 125]} {...axis} label={{ value: 'Actual RUL', position: 'insideBottom', offset: -8, fill: COLORS.muted, fontSize: 12 }} />
            <YAxis type="number" dataKey="predicted" name="Predicted" domain={[0, 130]} ticks={[0, 25, 50, 75, 100, 125]} {...axis} width={44} />
            <ZAxis range={[36, 36]} />
            <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 125, y: 125 }]} stroke={COLORS.muted} />
            <Tooltip
              cursor={false}
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <div className={tooltipBox}>
                    <div className="font-medium text-ink">{payload[0].payload.dataset}</div>
                    Actual {payload[0].payload.true} · predicted {payload[0].payload.predicted} ({payload[0].payload.low}–{payload[0].payload.high})
                  </div>
                ) : null
              }
            />
            <Scatter data={shown} fill={COLORS.predicted} fillOpacity={0.75} isAnimationActive={false}>
              <ErrorBar dataKey="err" direction="y" stroke={COLORS.predicted} strokeOpacity={0.25} width={0} />
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function ErrorByBand({ bands }) {
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={bands} margin={{ top: 20, right: 12, bottom: 16, left: 0 }}>
          <CartesianGrid stroke={COLORS.grid} vertical={false} />
          <XAxis dataKey="band" {...axis} label={{ value: 'True RUL (cycles)', position: 'insideBottom', offset: -8, fill: COLORS.muted, fontSize: 12 }} />
          <YAxis {...axis} width={44} />
          <Tooltip
            cursor={{ fill: COLORS.grid }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className={tooltipBox}>
                  True RUL {payload[0].payload.band}: MAE <span className="text-ink">{payload[0].payload.mae}</span> cycles, bias{' '}
                  {payload[0].payload.bias > 0 ? '+' : ''}
                  {payload[0].payload.bias} ({payload[0].payload.rows.toLocaleString()} cycles)
                </div>
              ) : null
            }
          />
          <Bar dataKey="mae" fill={COLORS.predicted} maxBarSize={24} radius={[4, 4, 0, 0]} isAnimationActive={false} label={{ position: 'top', fill: COLORS.ink2, fontSize: 12 }} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function Reliability({ bins }) {
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 12, bottom: 16, left: 0 }}>
          <CartesianGrid stroke={COLORS.grid} />
          <XAxis type="number" dataKey="predicted" domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={pct} {...axis} label={{ value: 'Predicted probability', position: 'insideBottom', offset: -8, fill: COLORS.muted, fontSize: 12 }} />
          <YAxis type="number" dataKey="observed" domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={pct} {...axis} width={44} />
          <ZAxis range={[64, 64]} />
          <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke={COLORS.muted} />
          <Tooltip
            cursor={false}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className={tooltipBox}>
                  Predicted {pct(payload[0].payload.predicted)} · happened {pct(payload[0].payload.observed)} ({payload[0].payload.rows.toLocaleString()} cycles)
                </div>
              ) : null
            }
          />
          <Scatter data={bins} fill={COLORS.predicted} stroke={COLORS.surface} strokeWidth={2} isAnimationActive={false} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}

function Importance({ items, sensors }) {
  const names = Object.fromEntries(sensors.map((s) => [s.sensor, `${s.symbol} · ${s.name}`]))
  const data = items.map((i) => ({ ...i, name: i.feature === 'cycle' ? 'Age · cycles in service' : names[i.feature] }))
  const max = Math.max(...data.map((d) => d.mean_abs_cycles))
  return (
    <table className="w-full text-sm">
      <tbody>
        {data.map((d) => (
          <tr key={d.feature}>
            <th scope="row" className="w-56 py-1 pr-3 text-left font-normal text-ink-secondary">
              {d.name}
            </th>
            <td className="py-1">
              <div className="h-3 rounded-r" style={{ width: `${(d.mean_abs_cycles / max) * 100}%`, background: COLORS.predicted }} />
            </td>
            <td className="w-14 py-1 pl-3 text-right text-ink-secondary tabular">{d.mean_abs_cycles.toFixed(1)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
