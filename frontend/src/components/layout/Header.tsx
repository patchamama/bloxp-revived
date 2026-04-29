import { NavLink } from 'react-router-dom'

export function Header() {
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
          <NavLink to="/about" className={linkClass}>
            About
          </NavLink>
          <NavLink to="/faq" className={linkClass}>
            FAQ
          </NavLink>
          <NavLink to="/contact" className={linkClass}>
            Contact
          </NavLink>
        </nav>
      </div>
    </header>
  )
}
