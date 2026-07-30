import { useState, useRef, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Send, Trash2, Bot, User, ChevronDown, ChevronRight, Zap, Loader2 } from 'lucide-react'
import { chatAPI } from '../../api/chat'
import { agentsAPI } from '../../api/agents'
import { cn } from '../../lib/utils'

export default function ChatPage() {
  const { id } = useParams()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)
  const queryClient = useQueryClient()

  const { data: agentData } = useQuery({
    queryKey: ['agent', id],
    queryFn: () => agentsAPI.get(id),
  })

  const { isLoading: historyLoading } = useQuery({
    queryKey: ['chatHistory', id],
    queryFn: async () => {
      const { data } = await chatAPI.history(id)
      setMessages(data.messages || [])
      return data
    },
  })

  const sendMutation = useMutation({
    mutationFn: (message) => chatAPI.send(id, { message }),
    onSuccess: ({ data }) => {
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: input, created_at: new Date().toISOString() },
        {
          role: 'assistant',
          content: data.content,
          tool_calls: data.tool_calls || [],
          tool_results: data.tool_results || [],
          tokens_used: data.tokens_used,
          model: data.model,
          created_at: data.created_at,
        },
      ])
      setInput('')
      queryClient.invalidateQueries({ queryKey: ['chatHistory', id] })
    },
  })

  const clearMutation = useMutation({
    mutationFn: () => chatAPI.clear(id),
    onSuccess: () => {
      setMessages([])
      queryClient.invalidateQueries({ queryKey: ['chatHistory', id] })
    },
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sendMutation.isPending])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || sendMutation.isPending) return
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: trimmed, created_at: new Date().toISOString() },
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

  const agent = agentData?.data

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium">{agent?.name || 'Agent'}</span>
          {agent && (
            <span className="rounded-md bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
              {agent.model_name}
            </span>
          )}
        </div>
        <button
          onClick={() => clearMutation.mutate()}
          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground"
        >
          <Trash2 className="h-3.5 w-3.5" />
          Clear chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {historyLoading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
            <Bot className="mb-3 h-12 w-12 opacity-20" />
            <p className="text-lg font-medium">Start a conversation</p>
            <p className="text-sm">Send a message to {agent?.name || 'this agent'}</p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
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
            disabled={!input.trim() || sendMutation.isPending}
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
