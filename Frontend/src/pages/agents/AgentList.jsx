import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bot, MessageSquare, Edit3, Trash2, Plus, Loader2 } from 'lucide-react';
import { agentsAPI } from '../../api/agents';
import { conversationsAPI } from '../../api/conversations';
import { cn } from '../../lib/utils';

const engineLabels = {
  langchain: 'LangChain',
  langgraph: 'LangGraph',
  custom_llm: 'Custom LLM',
};

const engineColors = {
  langchain: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  langgraph: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
  custom_llm: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
};

export default function AgentList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [deleteId, setDeleteId] = useState(null);
  const [chatLoadingId, setChatLoadingId] = useState(null);

  const createConvMutation = useMutation({
    mutationFn: (agentId) => conversationsAPI.create({ agent_id: agentId, title: 'New Conversation' }),
    onSuccess: ({ data }) => {
      setChatLoadingId(null);
      navigate(`/conversations/${data.id}`);
    },
    onError: () => setChatLoadingId(null),
  });

  const { data: responseData, isLoading, error } = useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const res = await agentsAPI.list()
      return res.data
    },
  });
  const agents = responseData?.agents ?? [];

  const deleteMutation = useMutation({
    mutationFn: (id) => agentsAPI.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      setDeleteId(null);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-destructive">Failed to load agents. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Agents</h1>
          <p className="text-muted-foreground mt-1">Manage your AI agents</p>
        </div>
        <Link
          to="/agents/new"
          className="inline-flex items-center gap-2 bg-primary text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Create Agent
        </Link>
      </div>

      {agents.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-80 border border-dashed border-border rounded-xl">
          <Bot className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-foreground font-medium">No agents yet</p>
          <p className="text-muted-foreground text-sm mt-1 mb-4">Create your first agent to get started</p>
          <Link
            to="/agents/new"
            className="inline-flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create Agent
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="bg-card border border-border rounded-xl p-5 hover:border-primary/30 transition-colors flex flex-col"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-primary/15 flex items-center justify-center shrink-0">
                    <Bot className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-foreground font-semibold truncate">{agent.name}</h3>
                    <p className="text-muted-foreground text-xs truncate">{agent.model_name}</p>
                  </div>
                </div>
                <span
                  className={cn(
                    'shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full border',
                    agent.status === 'active' ? 'bg-success/15 text-success border-success/30' : 'bg-secondary text-muted-foreground border-border'
                  )}
                >
                  {agent.status || 'draft'}
                </span>
              </div>

              <p className="text-muted-foreground text-sm mb-4 line-clamp-2 flex-1">
                {agent.description || 'No description'}
              </p>

              <div className="flex items-center gap-2 mb-4">
                <span
                  className={cn(
                    'text-[11px] font-medium px-2 py-0.5 rounded border',
                    engineColors[agent.engine] || 'bg-secondary text-muted-foreground border-border'
                  )}
                >
                  {engineLabels[agent.engine] || agent.engine}
                </span>
              </div>

              <div className="flex items-center gap-2 pt-3 border-t border-border">
                <button
                  onClick={() => {
                    setChatLoadingId(agent.id);
                    createConvMutation.mutate(agent.id);
                  }}
                  disabled={chatLoadingId === agent.id}
                  className="flex-1 inline-flex items-center justify-center gap-1.5 bg-primary/10 text-primary px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-primary/20 transition-colors disabled:opacity-50"
                >
                  {chatLoadingId === agent.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <MessageSquare className="h-3.5 w-3.5" />
                  )}
                  Chat
                </button>
                <Link
                  to={`/agents/${agent.id}/edit`}
                  className="inline-flex items-center justify-center gap-1.5 bg-secondary text-muted-foreground px-3 py-1.5 rounded-lg text-xs font-medium hover:text-foreground hover:bg-secondary/80 transition-colors"
                >
                  <Edit3 className="h-3.5 w-3.5" />
                  Edit
                </Link>
                <button
                  onClick={() => setDeleteId(agent.id)}
                  className="inline-flex items-center justify-center gap-1.5 bg-secondary text-muted-foreground px-3 py-1.5 rounded-lg text-xs font-medium hover:text-destructive hover:bg-destructive/10 transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {deleteId && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setDeleteId(null)}>
          <div
            className="bg-card border border-border rounded-xl p-6 w-full max-w-sm mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-foreground font-semibold mb-2">Delete Agent</h3>
            <p className="text-muted-foreground text-sm mb-6">
              Are you sure you want to delete this agent? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteId(null)}
                className="px-4 py-2 bg-secondary text-muted-foreground rounded-lg text-sm font-medium hover:text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteId)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-destructive text-white rounded-lg text-sm font-medium hover:bg-destructive/90 transition-colors disabled:opacity-50 inline-flex items-center gap-2"
              >
                {deleteMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
