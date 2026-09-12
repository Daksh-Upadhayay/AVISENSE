import { useState } from 'react'
import { api } from '../lib/api'
import { Button, ErrorNote, Field, Modal, Note, inputClass } from './ui'

export function AddEngineModal({ open, onClose, onCreated }) {
  const [form, setForm] = useState({ engine_id: '', model: '', serial_number: '', aircraft_registration: '' })
  const [file, setFile] = useState(null)
  const [unit, setUnit] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    let engine = null
    try {
      const fields = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v.trim() || null]))
      engine = await api.createEngine(fields)
      if (file) await api.upload(engine.id, file, { unit: unit || null, replace: false })
      onCreated(engine)
    } catch (err) {
      // The engine exists even if the upload failed; send the user there to retry.
      if (engine) onCreated(engine, err)
      else setError(err)
    } finally {
      setBusy(false)
    }
  }

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })
  return (
    <Modal open={open} onClose={onClose} title="Add an engine">
      <form onSubmit={submit} className="space-y-4">
        <ErrorNote error={error} />
        <Field label="Name">{(id) => <input id={id} required maxLength={64} placeholder="ENG-042" className={inputClass} value={form.engine_id} onChange={set('engine_id')} />}</Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Engine model (optional)">{(id) => <input id={id} className={inputClass} placeholder="CFM56-7B" value={form.model} onChange={set('model')} />}</Field>
          <Field label="Serial number (optional)">{(id) => <input id={id} className={inputClass} value={form.serial_number} onChange={set('serial_number')} />}</Field>
        </div>
        <Field label="Cycle history (optional)" hint="CSV with a header row, or a NASA C-MAPSS text file. You can also upload later.">
          {(id) => (
            <input id={id} type="file" accept=".csv,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="block w-full text-sm text-ink-secondary file:mr-3 file:rounded-md file:border-0 file:bg-surface-raised file:px-3 file:py-2 file:text-ink" />
          )}
        </Field>
        {file && (
          <Field label="Unit number" hint="Only needed when the file holds several engines.">
            {(id) => <input id={id} type="number" min="1" className={inputClass} value={unit} onChange={(e) => setUnit(e.target.value)} />}
          </Field>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={busy}>
            Add engine
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export function UploadModal({ open, onClose, engine, onDone }) {
  const [file, setFile] = useState(null)
  const [unit, setUnit] = useState('')
  const [replace, setReplace] = useState(false)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      onDone(await api.upload(engine.id, file, { unit: unit || null, replace }))
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={`Upload cycles for ${engine.engine_id}`}>
      <form onSubmit={submit} className="space-y-4">
        <ErrorNote error={error} />
        <Note>
          Needs <code className="text-ink">cycle</code>, the three operating settings and 14 sensors (T24, T30, T50, P30, Nf, Nc, Ps30, phi, NRf,
          NRc, BPR, htBleed, W31, W32). Column names can be <code className="text-ink">sensor_N</code> or the symbol. NASA C-MAPSS text files work
          as they are.
        </Note>
        <Field label="File">
          {(id) => (
            <input id={id} type="file" required accept=".csv,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="block w-full text-sm text-ink-secondary file:mr-3 file:rounded-md file:border-0 file:bg-surface-raised file:px-3 file:py-2 file:text-ink" />
          )}
        </Field>
        <Field label="Unit number" hint="Only needed when the file holds several engines.">
          {(id) => <input id={id} type="number" min="1" className={inputClass} value={unit} onChange={(e) => setUnit(e.target.value)} />}
        </Field>
        <label className="flex items-center gap-2 text-sm text-ink-secondary">
          <input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} className="h-4 w-4 accent-accent" />
          Replace the existing history instead of appending
        </label>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={busy} disabled={!file}>
            Upload and assess
          </Button>
        </div>
      </form>
    </Modal>
  )
}
