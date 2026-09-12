import { useCallback, useEffect, useState } from 'react'
import { supabase } from './supabase'

const API_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function request(method, path, { json, form, auth = true } = {}) {
  const headers = {}
  if (auth) {
    const { data } = await supabase.auth.getSession()
    const token = data.session?.access_token
    if (!token) throw new ApiError('Sign in to continue', 401)
    headers.Authorization = `Bearer ${token}`
  }
  let body
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(json)
  } else if (form) {
    body = form
  }

  let response
  try {
    response = await fetch(`${API_URL}${path}`, { method, headers, body })
  } catch {
    throw new ApiError(`Cannot reach the Avisense API at ${API_URL}. Is the backend running?`, 0)
  }
  if (response.status === 401 && auth) {
    await supabase.auth.signOut()
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((d) => d.msg).join('; ')
      : payload.detail || payload.error || `Request failed (${response.status})`
    throw new ApiError(detail, response.status)
  }
  return response.status === 204 ? null : response.json()
}

export const api = {
  model: () => request('GET', '/api/model', { auth: false }),
  engines: () => request('GET', '/api/engines'),
  engine: (id) => request('GET', `/api/engines/${id}`),
  createEngine: (fields) => request('POST', '/api/engines', { json: fields }),
  deleteEngine: (id) => request('DELETE', `/api/engines/${id}`),
  assess: (id) => request('POST', `/api/engines/${id}/assess`),
  replay: (id, steps) => request('POST', `/api/engines/${id}/replay?steps=${steps}`),
  demoFleet: (size = 8) => request('POST', '/api/fleet/demo', { json: { size } }),
  upload: (id, file, { unit, replace }) => {
    const form = new FormData()
    form.append('file', file)
    if (unit) form.append('unit', String(unit))
    form.append('replace', replace ? 'true' : 'false')
    return request('POST', `/api/engines/${id}/upload`, { form })
  },
}

/** Load data on mount and whenever `deps` change. Returns { data, error, loading, reload, setData }. */
export function useApi(loader, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let live = true
    loader()
      .then((data) => live && setState({ data, error: null, loading: false }))
      .catch((error) => live && setState((s) => ({ data: s.data, error, loading: false })))
    return () => {
      live = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])
  const setData = useCallback((data) => setState({ data, error: null, loading: false }), [])
  return { ...state, reload, setData }
}
