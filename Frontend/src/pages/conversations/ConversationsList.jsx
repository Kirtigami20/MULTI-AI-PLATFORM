import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MessageSquare, Plus, Search, Trash2, Pencil, MessageCircle, Loader2, Check, X, Bot } from 'lucide-react'
import { conversationsAPI } from '../../api/conversations'
import { agentsAPI } from '../../api/agents'

function formatTimeAgo(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  return date.toLocaleDateString()
}

export default function ConversationsList() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editTitle, setEditTitle] = useState('')
  const [deleteId, setDeleteId] = useState(null)
  const [showAgentPicker, setShowAgentPicker] = useState(false)
  const agentPickerRef = useRef(null)

  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const { data } = await agentsAPI.list()
      return data
    },
  })

  const createMutation = useMutation({
    mutationFn: (agentId) =>
      conversationsAPI.create({ agent_id: agentId, title: 'New Conversation' }),
    onSuccess: ({ data }) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      navigate(`/conversations/${data.id}`)
    },
  })

  const { data: convData, isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: async () => {
      const { data } = await conversationsAPI.list()
      return data
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => conversationsAPI.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      setDeleteId(null)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, title }) => conversationsAPI.update(id, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      setEditingId(null)
    },
  })

  useEffect(() => {
    function handleClickOutside(e) {
      if (agentPickerRef.current && !agentPickerRef.current.contains(e.target)) {
        setShowAgentPicker(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const filtered = (convData?.conversations || []).filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  )

  const handleNewChat = () => {
    const agents = agentsData?.agents || []
    if (agents.length === 1) {
      createMutation.mutate(agents[0].id)
    } else if (agents.length > 1) {
      setShowAgentPicker(true)
    }
  }

  const handleOpenConversation = (conv) => {
    navigate(`/conversations/${conv.id}`)
  }

  const handleStartRename = (conv) => {
    setEditingId(conv.id)
    setEditTitle(conv.title)
  }

  const handleSaveRename = (id) => {
    if (editTitle.trim()) {
      updateMutation.mutate({ id, title: editTitle.trim() })
    }
  }

  const handleCancelRename = () => {
    setEditingId(null)
    setEditTitle('')
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium">Conversations</span>
          <span className="rounded-md bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
            {convData?.total || 0}
          </span>
        </div>
        <div className="relative">
          <button
            onClick={handleNewChat}
            disabled={createMutation.isPending}
            className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {createMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Plus className="h-3.5 w-3.5" />
            )}
            New Conversation
          </button>
          {showAgentPicker && (
            <div
              ref={agentPickerRef}
              className="absolute right-0 top-full z-50 mt-1 w-56 rounded-xl border border-border bg-card p-1 shadow-lg"
            >
              <p className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
                Select an agent
              </p>
              {(agentsData?.agents || []).map((agent) => (
                <button
                  key={agent.id}
                  onClick={() => {
                    createMutation.mutate(agent.id)
                    setShowAgentPicker(false)
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-secondary"
                >
                  <Bot className="h-4 w-4 text-primary" />
                  <span className="truncate">{agent.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="border-b border-border px-4 py-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-border bg-secondary py-2 pl-10 pr-4 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
            <MessageCircle className="mb-3 h-12 w-12 opacity-20" />
            <p className="text-lg font-medium">
              {search ? 'No conversations found' : 'No conversations yet'}
            </p>
            <p className="text-sm">
              {search ? 'Try a different search term' : 'Start chatting with an agent'}
            </p>
            {!search && (
              <button
                onClick={handleNewChat}
                disabled={createMutation.isPending}
                className="mt-4 flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {createMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                New Conversation
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filtered.map((conv) => (
              <div
                key={conv.id}
                className="group flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-secondary/50 transition-colors"
                onClick={() => handleOpenConversation(conv)}
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <MessageSquare className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  {editingId === conv.id ? (
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveRename(conv.id)
                          if (e.key === 'Escape') handleCancelRename()
                        }}
                        className="flex-1 rounded border border-border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                        autoFocus
                      />
                      <button
                        onClick={() => handleSaveRename(conv.id)}
                        className="rounded p-1 text-green-500 hover:bg-green-500/10"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={handleCancelRename}
                        className="rounded p-1 text-muted-foreground hover:bg-secondary"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ) : (
                    <p className="truncate text-sm font-medium">{conv.title}</p>
                  )}
                  <p className="truncate text-xs text-muted-foreground">
                    {conv.last_message || (
                      <span className="italic">No messages yet</span>
                    )}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{conv.agent}</span>
                    <span>·</span>
                    <span>{formatTimeAgo(conv.updated_at)}</span>
                  </div>
                </div>
                <div
                  className="hidden group-hover:flex items-center gap-1 shrink-0"
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    onClick={() => handleStartRename(conv)}
                    className="rounded-lg p-2 text-muted-foreground hover:bg-secondary hover:text-foreground"
                    title="Rename"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  {deleteId === conv.id ? (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => deleteMutation.mutate(conv.id)}
                        className="rounded-lg bg-destructive px-2 py-1.5 text-xs font-medium text-destructive-foreground hover:bg-destructive/90"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={() => setDeleteId(null)}
                        className="rounded-lg bg-secondary px-2 py-1.5 text-xs font-medium hover:bg-secondary/80"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDeleteId(conv.id)}
                      className="rounded-lg p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                      title="Delete"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
