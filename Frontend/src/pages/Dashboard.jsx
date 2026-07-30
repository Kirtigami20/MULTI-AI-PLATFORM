import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useNavigate, Link } from 'react-router-dom'
import { Bot, Database, Wrench, MessageSquare, Loader2 } from 'lucide-react'
import { agentsAPI } from '../api/agents'
import { conversationsAPI } from '../api/conversations'
import { knowledgeAPI } from '../api/knowledge'
import { toolsAPI } from '../api/tools'

const statCards = [
  { key: 'agents', label: 'Total Agents', icon: Bot },
  { key: 'knowledge', label: 'Knowledge Bases', icon: Database },
  { key: 'tools', label: 'Tools', icon: Wrench },
  { key: 'chat', label: 'Chat Sessions', icon: MessageSquare },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const [chatLoadingId, setChatLoadingId] = useState(null)

  const createConvMutation = useMutation({
    mutationFn: (agentId) => conversationsAPI.create({ agent_id: agentId, title: 'New Conversation' }),
    onSuccess: ({ data }) => {
      setChatLoadingId(null)
      navigate(`/conversations/${data.id}`)
    },
    onError: () => setChatLoadingId(null),
  })

  const { data: agentsRes } = useQuery({
    queryKey: ['agents'],
    queryFn: agentsAPI.list,
  })
  const { data: knowledgeRes } = useQuery({
    queryKey: ['knowledge'],
    queryFn: knowledgeAPI.list,
  })
  const { data: toolsRes } = useQuery({
    queryKey: ['tools'],
    queryFn: toolsAPI.list,
  })

  const agents = agentsRes?.data?.agents ?? []
  const knowledge = knowledgeRes?.data?.knowledge_bases ?? []
  const tools = toolsRes?.data?.tools ?? []

  const counts = {
    agents: agents.length,
    knowledge: knowledge.length,
    tools: tools.length,
    chat: agents.length,
  }

  const recentAgents = agents.slice(0, 6)

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map(({ key, label, icon: Icon }) => (
          <div
            key={key}
            className="flex items-center gap-4 rounded-xl border border-border bg-card p-5"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Icon className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold">{counts[key]}</p>
              <p className="text-sm text-muted-foreground">{label}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent Agents</h2>
          <Link
            to="/agents"
            className="text-sm text-primary hover:underline"
          >
            View all
          </Link>
        </div>

        {recentAgents.length === 0 ? (
          <div className="rounded-xl border border-border bg-card p-8 text-center text-muted-foreground">
            No agents yet. Create your first agent to get started.
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {recentAgents.map((agent) => (
              <button
                key={agent.id}
                onClick={() => {
                  setChatLoadingId(agent.id)
                  createConvMutation.mutate(agent.id)
                }}
                disabled={chatLoadingId === agent.id}
                className="group w-full rounded-xl border border-border bg-card p-5 transition-colors hover:border-primary/50 disabled:opacity-50"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    {chatLoadingId === agent.id ? (
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    ) : (
                      <Bot className="h-4 w-4 text-primary" />
                    )}
                  </div>
                  <div className="min-w-0 text-left">
                    <p className="truncate font-medium group-hover:text-primary">
                      {agent.name}
                    </p>
                    <p className="truncate text-sm text-muted-foreground">
                      {agent.description || 'No description'}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
