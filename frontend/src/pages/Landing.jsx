import { Link } from 'react-router-dom'
import { Activity, BarChart3, Search } from 'lucide-react'
import { api, useApi } from '../lib/api'
import { useAuth } from '../lib/auth'
import { Layout } from '../components/Layout'

const POINTS = [
  {
    icon: Activity,
    title: 'Remaining life with an honest range',
    text: 'Every estimate comes with an 80% range that is checked against real outcomes, plus the chance of failure within the next 30 cycles.',
  },
  {
    icon: Search,
    title: 'The reason behind every number',
    text: 'See which sensors moved the estimate and by how many cycles, and how far each sensor has drifted towards its typical failure level.',
  },
  {
    icon: BarChart3,
    title: 'Tested in the open',
    text: "Accuracy is measured on NASA's official C-MAPSS test engines and published on the model page, weaknesses included.",
  },
]

export default function Landing() {
  const { user } = useAuth()
  const card = useApi(() => api.model(), [])
  const o = card.data?.metrics.overall

  return (
    <Layout>
      <section className="max-w-3xl py-10">
        <h1 className="text-4xl font-semibold leading-tight text-ink sm:text-5xl">How long until this engine needs attention, and why?</h1>
        <p className="mt-5 text-lg text-ink-secondary">
          Avisense estimates the remaining useful life of turbofan engines from their cycle-by-cycle sensor history and explains each estimate
          in terms an engineer can check.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link to={user ? '/fleet' : '/signup'} className="rounded-md bg-accent-strong px-5 py-2.5 text-sm font-medium text-white hover:bg-accent">
            {user ? 'Open your fleet' : 'Try it with a demo fleet'}
          </Link>
          <Link to="/model" className="rounded-md border border-line-strong px-5 py-2.5 text-sm font-medium text-ink hover:bg-surface-raised">
            See how accurate it is
          </Link>
        </div>
        {o && (
          <p className="mt-6 text-sm text-ink-muted">
            On {o.engines} unseen NASA test engines: typical error {o.rmse} cycles (RMSE), {Math.round(o.recall * 100)}% of near-failure cycles
            flagged.
          </p>
        )}
      </section>

      <section className="grid gap-4 border-t border-line py-10 md:grid-cols-3">
        {POINTS.map(({ icon: Icon, title, text }) => (
          <div key={title}>
            <Icon className="h-5 w-5 text-accent" aria-hidden />
            <h2 className="mt-3 font-semibold text-ink">{title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-secondary">{text}</p>
          </div>
        ))}
      </section>

      <p className="border-t border-line pt-6 text-xs text-ink-muted">
        Trained on simulated engine data (NASA C-MAPSS). A research demonstration, not a certified maintenance tool.
      </p>
    </Layout>
  )
}
