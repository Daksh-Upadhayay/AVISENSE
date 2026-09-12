import { Suspense, lazy } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './lib/auth'
import { configError } from './lib/supabase'
import { Spinner } from './components/ui'
import Landing from './pages/Landing'
import { Login, Signup } from './pages/Auth'
import Fleet from './pages/Fleet'

// Chart-heavy pages load on demand to keep the first page small.
const EngineDetail = lazy(() => import('./pages/EngineDetail'))
const ModelCard = lazy(() => import('./pages/ModelCard'))

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  return user ? children : <Navigate to="/login" replace />
}

function PublicOnly({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  return user ? <Navigate to="/fleet" replace /> : children
}

export default function App() {
  if (configError) {
    return (
      <div className="mx-auto max-w-lg p-10 text-sm text-ink-secondary">
        <h1 className="mb-2 text-lg font-semibold text-ink">Avisense is not configured</h1>
        {configError}
      </div>
    )
  }
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<Spinner />}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/model" element={<ModelCard />} />
            <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
            <Route path="/signup" element={<PublicOnly><Signup /></PublicOnly>} />
            <Route path="/fleet" element={<RequireAuth><Fleet /></RequireAuth>} />
            <Route path="/engines/:id" element={<RequireAuth><EngineDetail /></RequireAuth>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  )
}
