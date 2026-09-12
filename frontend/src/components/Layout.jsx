import { Link, NavLink, useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { useAuth } from '../lib/auth'

export function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2 font-semibold text-ink">
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden>
        <rect width="32" height="32" rx="7" fill="#222220" />
        <path d="M6 24 L16 7 L26 24" fill="none" stroke="#3987e5" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M10.5 18 H21.5" stroke="#c3c2b7" strokeWidth="2.5" strokeLinecap="round" />
      </svg>
      Avisense
    </Link>
  )
}

const navClass = ({ isActive }) =>
  `rounded-md px-3 py-1.5 text-sm transition-colors ${isActive ? 'bg-surface-raised text-ink' : 'text-ink-secondary hover:text-ink'}`

export function Layout({ children }) {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-page">
      <header className="sticky top-0 z-40 border-b border-line bg-page/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 sm:gap-6 sm:px-6">
          <Logo />
          <nav className="flex items-center gap-1">
            {user && (
              <NavLink to="/fleet" className={navClass}>
                Fleet
              </NavLink>
            )}
            <NavLink to="/model" className={navClass}>
              Model
            </NavLink>
          </nav>
          <div className="ml-auto flex items-center gap-3">
            {user ? (
              <>
                <span className="hidden text-sm text-ink-muted sm:inline">{user.email}</span>
                <button
                  onClick={async () => {
                    await signOut()
                    navigate('/')
                  }}
                  className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm text-ink-secondary hover:bg-surface-hover hover:text-ink"
                  aria-label="Sign out"
                >
                  <LogOut className="h-4 w-4" aria-hidden />
                  <span className="hidden sm:inline">Sign out</span>
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-sm text-ink-secondary hover:text-ink">
                  Sign in
                </Link>
                <Link to="/signup" className="rounded-md bg-accent-strong px-3 py-1.5 text-sm font-medium text-white hover:bg-accent">
                  Create account
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">{children}</main>
    </div>
  )
}
