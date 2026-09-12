import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plane, Plus, Sparkles } from 'lucide-react'
import { api, useApi } from '../lib/api'
import { STATUS, formatProbability, formatRul, relativeTime, replayOf } from '../lib/format'
import { Layout } from '../components/Layout'
import { AddEngineModal } from '../components/EngineModals'
import { Button, Card, ErrorNote, Spinner, Stat, StatusBadge } from '../components/ui'

const CAP = 125

function sortKey(e) {
  const h = e.health
  if (!h) return [3, 0]
  return [STATUS[h.status]?.rank ?? 3, h.rul]
}

/** Small horizontal meter: RUL range on a 0-125 scale, point estimate as a tick. */
function RulMeter({ health }) {
  if (!health) return null
  const pct = (v) => `${(Math.min(v, CAP) / CAP) * 100}%`
  return (
    <div className="relative mt-1 h-1.5 w-28 rounded-full bg-surface-hover" aria-hidden>
      <div className="absolute h-full rounded-full bg-accent/40" style={{ left: pct(health.rul_low), width: `calc(${pct(health.rul_high)} - ${pct(health.rul_low)})` }} />
      <div className="absolute -top-0.5 h-2.5 w-0.5 rounded bg-ink" style={{ left: pct(health.rul) }} />
    </div>
  )
}

export default function Fleet() {
  const navigate = useNavigate()
  const engines = useApi(() => api.engines(), [])
  const [adding, setAdding] = useState(false)
  const [demoBusy, setDemoBusy] = useState(false)
  const [actionError, setActionError] = useState(null)

  const list = useMemo(() => {
    const rows = [...(engines.data ?? [])]
    rows.sort((a, b) => {
      const [ra, ua] = sortKey(a)
      const [rb, ub] = sortKey(b)
      return ra - rb || ua - ub
    })
    return rows
  }, [engines.data])

  const counts = useMemo(() => {
    const c = { critical: 0, watch: 0, healthy: 0 }
    for (const e of list) if (e.health) c[e.health.status] += 1
    return c
  }, [list])

  async function createDemo() {
    setDemoBusy(true)
    setActionError(null)
    try {
      await api.demoFleet(8)
      engines.reload()
    } catch (err) {
      setActionError(err)
    } finally {
      setDemoBusy(false)
    }
  }

  return (
    <Layout>
      <AddEngineModal
        open={adding}
        onClose={() => setAdding(false)}
        onCreated={(engine) => {
          setAdding(false)
          navigate(`/engines/${engine.id}`)
        }}
      />

      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Fleet</h1>
          <p className="mt-1 text-sm text-ink-muted">Engines sorted by urgency. Remaining useful life (RUL) is in engine cycles.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={createDemo} loading={demoBusy}>
            <Sparkles className="h-4 w-4" aria-hidden /> Add demo engines
          </Button>
          <Button onClick={() => setAdding(true)}>
            <Plus className="h-4 w-4" aria-hidden /> Add engine
          </Button>
        </div>
      </div>

      <ErrorNote error={actionError || engines.error} className="mb-4" />

      {engines.loading && !engines.data ? (
        <Spinner label="Loading fleet" />
      ) : list.length === 0 ? (
        <Card className="py-14 text-center">
          <Plane className="mx-auto h-10 w-10 text-ink-muted" aria-hidden />
          <h2 className="mt-4 text-lg font-semibold text-ink">No engines yet</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-ink-muted">
            Start with a demo fleet: eight engines replayed cycle by cycle from NASA's C-MAPSS test data, so you can compare every prediction with
            the real outcome. Or add your own engine and upload its cycle history.
          </p>
          <div className="mt-6 flex justify-center gap-2">
            <Button onClick={createDemo} loading={demoBusy}>
              <Sparkles className="h-4 w-4" aria-hidden /> Create demo fleet
            </Button>
            <Button variant="secondary" onClick={() => setAdding(true)}>
              Add my own engine
            </Button>
          </div>
        </Card>
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Engines" value={list.length} />
            {['critical', 'watch', 'healthy'].map((s) => {
              const Icon = STATUS[s].icon
              return (
                <Stat key={s} label={STATUS[s].label} value={counts[s]}>
                  <Icon className="h-4 w-4 self-center" style={{ color: STATUS[s].color }} aria-hidden />
                </Stat>
              )
            })}
          </div>

          <Card className="overflow-x-auto p-0">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs text-ink-muted">
                  <th className="px-5 py-3 font-medium">Engine</th>
                  <th className="px-3 py-3 font-medium">Status</th>
                  <th className="px-3 py-3 font-medium">RUL (80% range)</th>
                  <th className="px-3 py-3 font-medium">Failure within 30 cycles</th>
                  <th className="px-3 py-3 font-medium">Cycle</th>
                  <th className="px-5 py-3 font-medium">Assessed</th>
                </tr>
              </thead>
              <tbody>
                {list.map((e) => {
                  const h = e.health
                  const replay = replayOf(e)
                  return (
                    <tr key={e.id} className="border-b border-line last:border-0 hover:bg-surface-raised">
                      <td className="px-5 py-3">
                        <Link to={`/engines/${e.id}`} className="font-medium text-ink hover:underline">
                          {e.engine_id}
                        </Link>
                        <div className="text-xs text-ink-muted">{replay ? `NASA ${replay.dataset} replay` : e.model || 'Uploaded data'}</div>
                      </td>
                      <td className="px-3 py-3">
                        <StatusBadge status={h?.status} />
                      </td>
                      <td className="px-3 py-3 tabular">
                        {h ? (
                          <>
                            <span className="font-medium text-ink">{formatRul(h.rul)}</span>{' '}
                            <span className="text-ink-muted">
                              ({Math.round(h.rul_low)}–{formatRul(h.rul_high)})
                            </span>
                            <RulMeter health={h} />
                          </>
                        ) : (
                          <span className="text-ink-muted">No data</span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-ink-secondary tabular">{h ? formatProbability(h.failure_probability) : '—'}</td>
                      <td className="px-3 py-3 text-ink-secondary tabular">
                        {h ? h.cycle : '—'}
                        {replay && <span className="text-ink-muted"> / {replay.length}</span>}
                      </td>
                      <td className="px-5 py-3 text-ink-muted">{h ? relativeTime(h.assessed_at) : '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </Layout>
  )
}
