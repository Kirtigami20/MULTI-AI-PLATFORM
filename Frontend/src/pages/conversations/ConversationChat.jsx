import { useState, useRef, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Send, Bot, User, ArrowLeft, Trash2, Pencil, Check, X, ChevronDown, ChevronRight, Zap, Loader2 } from 'lucide-react'
import { conversationsAPI } from '../../api/conversations'
import { agentsAPI } from '../../api/agents'
import { chatAPI } from '../../api/chat'
import { cn } from '../../lib/utils'

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
  return `${diffDays} days ago`
}

export default function ConversationChat() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  const { data: convData } = useQuery({
    queryKey: ['conversation-meta', conversationId],
    queryFn: async () => {
      const { data } = await conversationsAPI.meta(conversationId)
      return data
    },
  })

  const { data: agentData } = useQuery({
    queryKey: ['agent', convData?.agent_id],
    queryFn: async () => {
      const { data } = await agentsAPI.get(convData.agent_id)
      return data
    },
    enabled: !!convData?.agent_id,
  })

  const { isLoading: messagesLoading } = useQuery({
    queryKey: ['conversation-messages', conversationId],
    queryFn: async () => {
      const { data } = await conversationsAPI.get(conversationId)
      setMessages(data.messages || [])
      return data
    },
  })

  const sendMutation = useMutation({
    mutationFn: (message) =>
      chatAPI.send(convData?.agent_id, { message, conversation_id: conversationId }),
    onSuccess: ({ data }) => {
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: input, timestamp: new Date().toISOString() },
        {
          role: 'assistant',
          content: data.content,
          tool_calls: data.tool_calls || [],
          tool_results: data.tool_results || [],
          tokens_used: data.tokens_used,
          model: data.model,
          timestamp: data.created_at,
        },
      ])
      setInput('')
      queryClient.invalidateQueries({ queryKey: ['conversation-messages', conversationId] })
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => conversationsAPI.delete(conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      navigate('/conversations')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (title) => conversationsAPI.update(conversationId, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      queryClient.invalidateQueries({ queryKey: ['conversation-meta', conversationId] })
      setIsEditing(false)
    },
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sendMutation.isPending])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || sendMutation.isPending || !convData?.agent_id) return
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: trimmed, timestamp: new Date().toISOString() },
    ])
    sendMutation.mutate(trimmed)
    setInput('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleStartEdit = () => {
    setIsEditing(true)
    setEditTitle(convData?.title || '')
  }

  const handleSaveTitle = () => {
    if (editTitle.trim()) {
      updateMutation.mutate(editTitle.trim())
    }
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <button
            onClick={() => navigate('/conversations')}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          {isEditing ? (
            <div className="flex items-center gap-1">
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveTitle()
                  if (e.key === 'Escape') setIsEditing(false)
                }}
                className="rounded border border-border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                autoFocus
              />
              <button
                onClick={handleSaveTitle}
                className="rounded p-1 text-green-500 hover:bg-green-500/10"
              >
                <Check className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setIsEditing(false)}
                className="rounded p-1 text-muted-foreground hover:bg-secondary"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">
                  {convData?.title || 'Conversation'}
                </p>
                {convData && (
                  <p className="text-xs text-muted-foreground">
                    {agentData?.name || 'Agent'} · {formatTimeAgo(convData.updated_at)}
                  </p>
                )}
              </div>
              <button
                onClick={handleStartEdit}
                className="rounded-lg p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
                title="Rename"
              >
                <Pencil className="h-3.5 w-3.5" />
              </button>
            </>
          )}
        </div>
        {showDeleteConfirm ? (
          <div className="flex items-center gap-2">
            <button
              onClick={() => deleteMutation.mutate()}
              className="rounded-lg bg-destructive px-3 py-1.5 text-xs font-medium text-destructive-foreground hover:bg-destructive/90"
            >
              Confirm Delete
            </button>
            <button
              onClick={() => setShowDeleteConfirm(false)}
              className="rounded-lg bg-secondary px-3 py-1.5 text-xs font-medium hover:bg-secondary/80"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messagesLoading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
            <Bot className="mb-3 h-12 w-12 opacity-20" />
            <p className="text-lg font-medium">Start a conversation</p>
            <p className="text-sm">Send a message to start chatting</p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <MessageBubble key={msg.id || i} message={msg} />
          ))
        )}
        {sendMutation.isPending && (
          <div className="flex gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            <div className="rounded-xl bg-secondary px-4 py-3">
              <div className="flex gap-1">
                <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground" />
              </div>
            </div>
          </div>
        )}
        {sendMutation.isError && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
            Error: {sendMutation.error?.response?.data?.detail || 'Failed to send message'}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-border p-4">
        <div className="flex gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={1}
            className="flex-1 resize-none rounded-xl border border-border bg-secondary px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sendMutation.isPending || !convData?.agent_id}
            className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const [expanded, setExpanded] = useState(false)
  const hasTools = message.tool_calls?.length > 0

  return (
    <div className={cn('flex gap-3', isUser && 'flex-row-reverse')}>
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary/20' : 'bg-primary/10'
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-primary" />
        ) : (
          <Bot className="h-4 w-4 text-primary" />
        )}
      </div>

      <div className={cn('max-w-[75%] space-y-1', isUser && 'flex flex-col items-end')}>
        <div
          className={cn(
            'rounded-2xl px-4 py-2.5 text-sm',
            isUser
              ? 'bg-primary text-primary-foreground rounded-br-md'
              : 'bg-secondary text-foreground rounded-bl-md'
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {hasTools && (
          <div className="w-full">
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              {expanded ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
              {message.tool_calls.length} tool call{message.tool_calls.length > 1 ? 's' : ''}
            </button>
            {expanded && (
              <div className="mt-1 space-y-1 rounded-lg border border-border bg-background p-2">
                {message.tool_calls.map((tc, i) => (
                  <div key={tc.id || i} className="text-xs">
                    <div className="flex items-center gap-1.5">
                      <Zap className="h-3 w-3 text-warning" />
                      <span className="font-medium">{tc.name}</span>
                    </div>
                    <pre className="mt-1 overflow-x-auto text-muted-foreground">
                      {JSON.stringify(tc.arguments, null, 2)}
                    </pre>
                    {message.tool_results?.[i] && (
                      <pre className="mt-1 overflow-x-auto text-muted-foreground">
                        Result: {message.tool_results[i].result}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {!isUser && (message.tokens_used > 0 || message.model) && (
          <div className="flex gap-2 text-xs text-muted-foreground">
            {message.model && <span>{message.model}</span>}
            {message.tokens_used > 0 && <span>{message.tokens_used} tokens</span>}
          </div>
        )}
      </div>
    </div>
  )
}
