import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { Layout } from '../components/Layout'
import { Button, Card, ErrorNote, Field, inputClass } from '../components/ui'

function AuthShell({ title, subtitle, children, footer }) {
  return (
    <Layout>
      <div className="mx-auto mt-8 max-w-sm">
        <h1 className="text-2xl font-semibold text-ink">{title}</h1>
        <p className="mt-1 text-sm text-ink-muted">{subtitle}</p>
        <Card className="mt-6">{children}</Card>
        <p className="mt-4 text-center text-sm text-ink-muted">{footer}</p>
      </div>
    </Layout>
  )
}

export function Login() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signIn(form.email, form.password)
      navigate('/fleet')
    } catch (err) {
      setError(err)
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title="Sign in"
      subtitle="Open your fleet."
      footer={
        <>
          No account yet? <Link to="/signup" className="text-accent-soft hover:underline">Create one</Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        <ErrorNote error={error} />
        <Field label="Email">
          {(id) => <input id={id} type="email" required autoComplete="email" className={inputClass} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />}
        </Field>
        <Field label="Password">
          {(id) => <input id={id} type="password" required autoComplete="current-password" className={inputClass} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />}
        </Field>
        <Button type="submit" loading={busy} className="w-full">
          Sign in
        </Button>
      </form>
    </AuthShell>
  )
}

export function Signup() {
  const { signUp } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ fullName: '', organization: '', email: '', password: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [sentTo, setSentTo] = useState(null)

  async function submit(e) {
    e.preventDefault()
    if (form.password.length < 8) {
      setError(new Error('Use at least 8 characters for the password.'))
      return
    }
    setBusy(true)
    setError(null)
    try {
      const { needsConfirmation } = await signUp(form.email, form.password, form.fullName, form.organization)
      if (needsConfirmation) setSentTo(form.email)
      else navigate('/fleet')
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  if (sentTo) {
    return (
      <AuthShell title="Check your email" subtitle={`We sent a confirmation link to ${sentTo}.`} footer={<Link to="/login" className="text-accent-soft hover:underline">Back to sign in</Link>}>
        <p className="text-sm text-ink-secondary">Open the link to activate your account, then sign in.</p>
      </AuthShell>
    )
  }

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })
  return (
    <AuthShell
      title="Create an account"
      subtitle="Your engines and their data are visible only to you."
      footer={
        <>
          Already have an account? <Link to="/login" className="text-accent-soft hover:underline">Sign in</Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        <ErrorNote error={error} />
        <Field label="Full name">{(id) => <input id={id} required autoComplete="name" className={inputClass} value={form.fullName} onChange={set('fullName')} />}</Field>
        <Field label="Organization (optional)">{(id) => <input id={id} autoComplete="organization" className={inputClass} value={form.organization} onChange={set('organization')} />}</Field>
        <Field label="Email">{(id) => <input id={id} type="email" required autoComplete="email" className={inputClass} value={form.email} onChange={set('email')} />}</Field>
        <Field label="Password" hint="At least 8 characters.">
          {(id) => <input id={id} type="password" required autoComplete="new-password" className={inputClass} value={form.password} onChange={set('password')} />}
        </Field>
        <Button type="submit" loading={busy} className="w-full">
          Create account
        </Button>
      </form>
    </AuthShell>
  )
}
