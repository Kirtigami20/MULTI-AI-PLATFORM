import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import { Menu, X } from 'lucide-react'
import { useState } from 'react'

const pageTitles = {
  '/': 'Dashboard',
  '/agents': 'Agents',
  '/agents/new': 'Create Agent',
  '/knowledge': 'Knowledge Bases',
  '/knowledge/new': 'Create Knowledge Base',
  '/tools': 'Tools',
  '/tools/new': 'Create Tool',
  '/upload': 'Upload Files',
}

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  const getTitle = () => {
    if (location.pathname.includes('/chat')) return 'Chat'
    if (location.pathname.includes('/edit')) return 'Edit Agent'
    return pageTitles[location.pathname] || 'AI Agent Platform'
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center gap-4 border-b border-border px-4 lg:px-6">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden text-muted-foreground hover:text-foreground"
          >
            <Menu className="h-5 w-5" />
          </button>
          <h1 className="text-lg font-semibold">{getTitle()}</h1>
        </header>

        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>

      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  )
}
