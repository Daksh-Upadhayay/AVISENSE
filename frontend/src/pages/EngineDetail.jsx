import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Pause, Play, RefreshCw, SkipForward, Trash2, Upload } from 'lucide-react'
import { api, useApi } from '../lib/api'
import { STATUS, formatDate, formatProbability, formatRul, replayOf } from '../lib/format'
import { Layout } from '../components/Layout'
import { UploadModal } from '../components/EngineModals'
import { SensorGrid } from '../components/SensorGrid'
import { RiskChart, RulChart } from '../components/charts/RulChart'
import { Waterfall } from '../components/charts/Waterfall'
import { Button, Card, ErrorNote, Note, SectionTitle, Spinner, StatusBadge } from '../components/ui'

const PLAY_STEP = 2
const PLAY_INTERVAL_MS = 1200

export default function EngineDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const detail = useApi(() => api.engine(id), [id])
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [playing, setPlaying] = useState(false)
  const timer = useRef(null)

  const engine = detail.data?.engine
  const analysis = detail.data?.analysis
  const replay = replayOf(engine)
  const finished = replay && replay.cursor >= replay.length

  async function run(label, action) {
    setBusy(label)
    setError(null)
    try {
      const result = await action()
      if (result) detail.setData(result)
      return result
    } catch (err) {
      setError(err)
      setPlaying(false)
    } finally {
      setBusy(null)
    }
  }

  // Auto-play: advance the replay a couple of cycles at a time until paused or finished.
  useEffect(() => {
    if (!playing || finished) return
    timer.current = setTimeout(() => run('play', () => api.replay(id, PLAY_STEP)), PLAY_INTERVAL_MS)
    return () => clearTimeout(timer.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, finished, detail.data])

  async function remove() {
    if (!window.confirm(`Delete ${engine.engine_id} and all its data? This cannot be undone.`)) return
    await run('delete', () => api.deleteEngine(id))
    navigate('/fleet')
  }

  if (detail.loading && !detail.data) {
    return (
      <Layout>
        <Spinner label="Loading engine" />
      </Layout>
    )
  }
  if (!engine) {
    return (
      <Layout>
        <ErrorNote error={detail.error || new Error('Engine not found')} />
        <Link to="/fleet" className="mt-4 inline-block text-sm text-accent-soft hover:underline">
          Back to fleet
        </Link>
      </Layout>
    )
  }

  const policy = analysis?.policy
  const cap = policy?.rul_cap ?? 125
  const trueNow = analysis?.trajectory.at(-1)?.true_rul
  const playingNow = playing && !finished

  return (
    <Layout>
      {!replay && (
        <UploadModal
          open={uploading}
          engine={engine}
          onClose={() => setUploading(false)}
          onDone={(result) => {
            setUploading(false)
            detail.setData(result)
          }}
        />
      )}

      <Link to="/fleet" className="mb-4 inline-flex items-center gap-1 text-sm text-ink-muted hover:text-ink">
        <ArrowLeft className="h-4 w-4" aria-hidden /> Fleet
      </Link>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold text-ink">{engine.engine_id}</h1>
            {analysis && <StatusBadge status={analysis.status} size="lg" />}
          </div>
          <p className="mt-1 text-sm text-ink-muted">
            {replay
              ? `Replaying NASA C-MAPSS ${replay.dataset}, test unit ${replay.unit} · cycle ${replay.cursor} of ${replay.length} available`
              : [engine.model, engine.serial_number].filter(Boolean).join(' · ') || 'Uploaded cycle history'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {replay ? (
            <>
              <Button variant="secondary" onClick={() => run('step', () => api.replay(id, 1))} loading={busy === 'step'} disabled={finished || playingNow}>
                <SkipForward className="h-4 w-4" aria-hidden /> Next cycle
              </Button>
              <Button variant="secondary" onClick={() => run('step10', () => api.replay(id, 10))} loading={busy === 'step10'} disabled={finished || playingNow}>
                +10 cycles
              </Button>
              <Button onClick={() => setPlaying((p) => !p)} disabled={finished}>
                {playingNow ? <Pause className="h-4 w-4" aria-hidden /> : <Play className="h-4 w-4" aria-hidden />}
                {finished ? 'End of record' : playingNow ? 'Pause' : 'Play'}
              </Button>
            </>
          ) : (
            <>
              <Button variant="secondary" onClick={() => setUploading(true)}>
                <Upload className="h-4 w-4" aria-hidden /> Upload cycles
              </Button>
              {analysis && (
                <Button variant="secondary" onClick={() => run('assess', () => api.assess(id))} loading={busy === 'assess'}>
                  <RefreshCw className="h-4 w-4" aria-hidden /> Save assessment
                </Button>
              )}
            </>
          )}
          <Button variant="danger" onClick={remove} loading={busy === 'delete'} aria-label="Delete engine">
            <Trash2 className="h-4 w-4" aria-hidden />
          </Button>
        </div>
      </div>

      <ErrorNote error={error || detail.error} className="mb-4" />

      {!analysis ? (
        <Card className="py-12 text-center">
          <h2 className="text-lg font-semibold text-ink">No cycles recorded yet</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-ink-muted">Upload this engine's cycle history to get a remaining-life estimate and an explanation.</p>
          <Button className="mt-5" onClick={() => setUploading(true)}>
            <Upload className="h-4 w-4" aria-hidden /> Upload cycles
          </Button>
        </Card>
      ) : (
        <div className="space-y-6">
          <Headline analysis={analysis} cap={cap} trueNow={trueNow} />

          <div className="grid items-start gap-6 xl:grid-cols-5">
            <Card className="xl:col-span-3">
              <SectionTitle
                title="Remaining useful life over time"
                hint={
                  replay
                    ? 'Each point is what the model would have said at that cycle, using only the cycles up to that point. The grey line is the true remaining life, known because this is recorded NASA data.'
                    : 'Each point is what the model would have said at that cycle, using only the cycles up to that point.'
                }
              />
              <RulChart trajectory={analysis.trajectory} cap={cap} />
            </Card>
            <Card className="xl:col-span-2">
              <SectionTitle
                title="Why this estimate"
                hint="Exact SHAP contributions from the RUL model, grouped by sensor. They start from the average engine and add up to this engine's estimate."
              />
              <Waterfall explanation={analysis.explanation} rul={analysis.rul} cap={cap} />
            </Card>
          </div>

          <Card>
            <SectionTitle
              title={`Chance of failure within ${policy.horizon} cycles`}
              hint={`From a separate classifier. At ${formatProbability(policy.alert_threshold)} or higher the engine is marked critical. The Model page shows how often that threshold catches real failures.`}
            />
            <RiskChart trajectory={analysis.trajectory} threshold={policy.alert_threshold} horizon={policy.horizon} />
          </Card>

          <Card>
            <SectionTitle
              title="Sensor drift"
              hint="How far each sensor has moved from this engine's own starting level, after removing the effect of altitude, speed and throttle. Sorted by how close each is to the drift typically seen just before failure."
            />
            <SensorGrid sensors={analysis.sensors} cycles={analysis.trajectory.map((d) => d.cycle)} />
          </Card>

          <History assessments={detail.data.assessments} />
        </div>
      )}
    </Layout>
  )
}

function Headline({ analysis, cap, trueNow }) {
  const { policy } = analysis
  const status = STATUS[analysis.status]
  return (
    <Card>
      <div className="grid gap-6 lg:grid-cols-[auto_auto_1fr]">
        <div>
          <div className="text-sm text-ink-muted">Estimated remaining life</div>
          <div className="mt-1 text-5xl font-semibold text-ink">
            {formatRul(analysis.rul, cap)}
            <span className="ml-2 text-lg font-normal text-ink-muted">cycles</span>
          </div>
          <div className="mt-1 text-sm text-ink-secondary tabular">
            80% range {Math.round(analysis.rul_low)}–{formatRul(analysis.rul_high, cap)}
          </div>
          {trueNow != null && (
            <div className="mt-1 text-sm text-ink-muted tabular">Actual (NASA record): {trueNow} cycles</div>
          )}
        </div>
        <div className="lg:border-l lg:border-line lg:pl-6">
          <div className="text-sm text-ink-muted">Failure within {policy.horizon} cycles</div>
          <div className="mt-1 text-3xl font-semibold text-ink">{formatProbability(analysis.failure_probability)}</div>
          <div className="mt-1 text-sm text-ink-muted">at cycle {analysis.cycle}</div>
        </div>
        <div className="space-y-3 lg:border-l lg:border-line lg:pl-6">
          <p className="text-sm leading-relaxed text-ink">{analysis.explanation.summary}</p>
          <p className="text-xs text-ink-muted">
            <span className="font-medium text-ink-secondary">Why “{status.label}”: </span>
            critical when the failure chance is {formatProbability(policy.alert_threshold)} or more; watch when the low end of the range is{' '}
            {policy.watch_rul} cycles or less; healthy otherwise.
          </p>
          {analysis.warnings.map((w) => (
            <Note key={w}>{w}</Note>
          ))}
        </div>
      </div>
    </Card>
  )
}

function History({ assessments }) {
  if (!assessments?.length) return null
  return (
    <Card className="overflow-x-auto p-0">
      <div className="px-5 pt-5">
        <SectionTitle title="Saved assessments" hint="A record is saved each time new cycles arrive or you save one by hand." />
      </div>
      <table className="w-full min-w-[640px] text-sm">
        <thead>
          <tr className="border-y border-line text-left text-xs text-ink-muted">
            <th className="px-5 py-2 font-medium">When</th>
            <th className="px-3 py-2 font-medium">Cycle</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 font-medium">RUL (80% range)</th>
            <th className="px-3 py-2 font-medium">Failure ≤30</th>
            <th className="px-5 py-2 font-medium">Model</th>
          </tr>
        </thead>
        <tbody>
          {assessments.slice(0, 20).map((a) => (
            <tr key={a.id} className="border-b border-line last:border-0">
              <td className="px-5 py-2 text-ink-secondary">{formatDate(a.created_at)}</td>
              <td className="px-3 py-2 text-ink-secondary tabular">{a.cycle}</td>
              <td className="px-3 py-2">
                <StatusBadge status={a.status} />
              </td>
              <td className="px-3 py-2 text-ink-secondary tabular">
                {formatRul(a.rul)} ({Math.round(a.rul_low)}–{formatRul(a.rul_high)})
              </td>
              <td className="px-3 py-2 text-ink-secondary tabular">{formatProbability(a.failure_probability)}</td>
              <td className="px-5 py-2 text-ink-muted">v{a.model_version}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}
