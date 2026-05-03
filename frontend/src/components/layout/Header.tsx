import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

const HISTORY_KEY = 'bloxp_job_history'

export function Header() {
  const location = useLocation()
  const [historyCount, setHistoryCount] = useState(0)

  useEffect(() => {
    const update = () => {
      try {
        const raw = localStorage.getItem(HISTORY_KEY)
        const arr = raw ? JSON.parse(raw) : []
        setHistoryCount(Array.isArray(arr) ? arr.length : 0)
      } catch {
        setHistoryCount(0)
      }
    }
    update()
    window.addEventListener('storage', update)
    window.addEventListener('focus', update)
    return () => {
      window.removeEventListener('storage', update)
      window.removeEventListener('focus', update)
    }
  }, [location.pathname])

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `text-sm font-medium transition-colors hover:text-blue-600 dark:hover:text-blue-400 ${
      isActive ? 'text-blue-600 dark:text-blue-400' : 'text-gray-600 dark:text-gray-300'
    }`

  return (
    <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-10">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <NavLink
          to="/"
          className="text-2xl font-bold text-blue-600 dark:text-blue-400 tracking-tight"
        >
          bloxp
        </NavLink>
        <nav className="flex gap-6">
          <NavLink to="/" end className={linkClass}>
            Home
          </NavLink>
          <NavLink to="/advanced" className={linkClass}>
            Advanced
          </NavLink>
          <NavLink to="/history" className={linkClass}>
            My ebooks
            {historyCount > 0 && (
              <sup className="ml-1 text-[10px] text-blue-600 dark:text-blue-400 align-super">{historyCount}</sup>
            )}
          </NavLink>
          <NavLink to="/about" className={linkClass}>
            About
          </NavLink>
          <NavLink to="/faq" className={linkClass}>
            FAQ
          </NavLink>
          <NavLink to="/contact" className={linkClass}>
            Contact
          </NavLink>
          <NavLink to="/admin" className={linkClass} title="Admin">
            🔐
          </NavLink>
        </nav>
      </div>
    </header>
  )
}
