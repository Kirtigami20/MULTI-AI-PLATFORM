import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect } from 'react'
import useAuthStore from './store/authStore'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import AgentList from './pages/agents/AgentList'
import AgentCreate from './pages/agents/AgentCreate'
import AgentEdit from './pages/agents/AgentEdit'
import KnowledgeList from './pages/knowledge/KnowledgeList'
import KnowledgeCreate from './pages/knowledge/KnowledgeCreate'
import ToolList from './pages/tools/ToolList'
import ToolCreate from './pages/tools/ToolCreate'
import ToolEdit from './pages/tools/ToolEdit'
import Upload from './pages/Upload'
import ConversationsList from './pages/conversations/ConversationsList'
import ConversationChat from './pages/conversations/ConversationChat'

const queryClient = new QueryClient()

function ProtectedRoute({ children }) {
  const { token, loading } = useAuthStore()
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }
  return token ? children : <Navigate to="/login" />
}

function PublicRoute({ children }) {
  const { token, loading } = useAuthStore()
  if (loading) return null
  return token ? <Navigate to="/" /> : children
}

export default function App() {
  const init = useAuthStore((s) => s.init)

  useEffect(() => {
    init()
  }, [init])

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
          <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="agents" element={<AgentList />} />
            <Route path="agents/new" element={<AgentCreate />} />
            <Route path="agents/:id/edit" element={<AgentEdit />} />
            <Route path="agents/:id/chat" element={<Navigate to="/conversations" replace />} />
            <Route path="knowledge" element={<KnowledgeList />} />
            <Route path="knowledge/new" element={<KnowledgeCreate />} />
            <Route path="tools" element={<ToolList />} />
            <Route path="tools/new" element={<ToolCreate />} />
            <Route path="tools/:id/edit" element={<ToolEdit />} />
            <Route path="upload" element={<Upload />} />
            <Route path="conversations" element={<ConversationsList />} />
            <Route path="conversations/:conversationId" element={<ConversationChat />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
