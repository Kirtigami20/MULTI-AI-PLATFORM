import { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Save, X } from 'lucide-react';
import { agentsAPI } from '../../api/agents';
import { knowledgeAPI } from '../../api/knowledge';
import { toolsAPI } from '../../api/tools';
import { cn } from '../../lib/utils';

const engines = [
  { value: 'langchain', label: 'LangChain', desc: 'Chain-based agent with tools' },
  { value: 'langgraph', label: 'LangGraph', desc: 'Graph-based stateful agent' },
  { value: 'custom_llm', label: 'Custom LLM', desc: 'Direct LLM with system prompt' },
];

export default function AgentEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState(null);
  const [blockedTopicsInput, setBlockedTopicsInput] = useState('');

  const { data: responseData, isLoading: agentLoading, error: agentError } = useQuery({
    queryKey: ['agent', id],
    queryFn: () => agentsAPI.get(id).then((r) => r.data),
  });
  const agent = responseData;

  const { data: kbData, isLoading: kbLoading } = useQuery({
    queryKey: ['knowledge'],
    queryFn: () => knowledgeAPI.list().then((r) => r.data),
  });
  const knowledgeBases = kbData?.knowledge_bases ?? [];

  const { data: toolsData, isLoading: toolsLoading } = useQuery({
    queryKey: ['tools'],
    queryFn: () => toolsAPI.list().then((r) => r.data),
  });
  const tools = toolsData?.tools ?? [];

  useEffect(() => {
    if (agent) {
      setForm({
        name: agent.name || '',
        description: agent.description || '',
        role: agent.role || '',
        goal: agent.goal || '',
        instructions: agent.instructions || '',
        system_prompt: agent.system_prompt || '',
        engine: agent.engine || 'langchain',
        model_name: agent.model_name || 'qwen2.5:3b',
        knowledge_base_ids: (agent.knowledge_bases || []).map((kb) => kb.id || kb),
        tool_ids: (agent.tools || []).map((t) => t.id || t),
        memory: {
          enabled: agent.memory?.enabled ?? true,
          window_size: agent.memory?.window_size ?? 10,
        },
        guardrails: {
          enabled: agent.guardrails?.enabled ?? false,
          max_tokens: agent.guardrails?.max_tokens ?? 4096,
          blocked_topics: agent.guardrails?.blocked_topics || [],
        },
      });
      if (agent.guardrails?.blocked_topics?.length) {
        setBlockedTopicsInput(agent.guardrails.blocked_topics.join(', '));
      }
    }
  }, [agent]);

  const updateMutation = useMutation({
    mutationFn: (data) => agentsAPI.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      queryClient.invalidateQueries({ queryKey: ['agent', id] });
      navigate('/agents');
    },
  });

  const updateField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const updateNested = (section, field, value) => {
    setForm((prev) => ({
      ...prev,
      [section]: { ...prev[section], [field]: value },
    }));
  };

  const toggleArrayItem = (field, itemId) => {
    setForm((prev) => {
      const arr = prev[field];
      return {
        ...prev,
        [field]: arr.includes(itemId) ? arr.filter((i) => i !== itemId) : [...arr, itemId],
      };
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const payload = {
      ...form,
      guardrails: {
        ...form.guardrails,
        blocked_topics: blockedTopicsInput
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
      },
    };
    updateMutation.mutate(payload);
  };

  if (agentLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (agentError || !form) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-3">
        <p className="text-destructive">Failed to load agent data.</p>
        <Link to="/agents" className="text-primary text-sm hover:underline">
          Back to agents
        </Link>
      </div>
    );
  }

  const isSubmitting = updateMutation.isPending;

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground">Edit Agent</h1>
        <p className="text-muted-foreground mt-1">Update agent configuration</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Basic Info */}
        <section className="bg-card border border-border rounded-xl p-6 space-y-5">
          <h2 className="text-foreground font-semibold text-lg">Basic Information</h2>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1.5">Name *</label>
            <input
              type="text"
              required
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
              placeholder="e.g. Research Assistant"
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1.5">Description</label>
            <textarea
              rows={2}
              value={form.description}
              onChange={(e) => updateField('description', e.target.value)}
              placeholder="What does this agent do?"
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1.5">Role</label>
            <input
              type="text"
              value={form.role}
              onChange={(e) => updateField('role', e.target.value)}
              placeholder="e.g. Senior Research Analyst"
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1.5">Goal</label>
            <textarea
              rows={2}
              value={form.goal}
              onChange={(e) => updateField('goal', e.target.value)}
              placeholder="Primary goal of the agent"
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1.5">Instructions</label>
            <textarea
              rows={3}
              value={form.instructions}
              onChange={(e) => updateField('instructions', e.target.value)}
              placeholder="Detailed instructions for the agent"
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1.5">System Prompt</label>
            <textarea
              rows={4}
              value={form.system_prompt}
              onChange={(e) => updateField('system_prompt', e.target.value)}
              placeholder="Override system prompt (optional)"
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary resize-none font-mono"
            />
          </div>
        </section>

        {/* Engine & Model */}
        <section className="bg-card border border-border rounded-xl p-6 space-y-5">
          <h2 className="text-foreground font-semibold text-lg">Engine & Model</h2>

          <div>
            <label className="block text-sm font-medium text-foreground mb-3">Engine *</label>
            <div className="grid grid-cols-3 gap-3">
              {engines.map((eng) => (
                <button
                  type="button"
                  key={eng.value}
                  onClick={() => updateField('engine', eng.value)}
                  className={cn(
                    'p-3 rounded-lg border text-left transition-colors',
                    form.engine === eng.value
                      ? 'border-primary bg-primary/10'
                      : 'border-border bg-background hover:border-muted-foreground/30'
                  )}
                >
                  <p className={cn('text-sm font-medium', form.engine === eng.value ? 'text-primary' : 'text-foreground')}>
                    {eng.label}
                  </p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">{eng.desc}</p>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1.5">Model Name</label>
            <input
              type="text"
              value={form.model_name}
              onChange={(e) => updateField('model_name', e.target.value)}
              placeholder="e.g. qwen2.5:3b"
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary font-mono"
            />
          </div>
        </section>

        {/* Knowledge Bases */}
        <section className="bg-card border border-border rounded-xl p-6 space-y-4">
          <h2 className="text-foreground font-semibold text-lg">Knowledge Bases</h2>
          {kbLoading ? (
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          ) : knowledgeBases.length === 0 ? (
            <p className="text-muted-foreground text-sm">No knowledge bases available</p>
          ) : (
            <div className="space-y-2">
              {knowledgeBases.map((kb) => (
                <label
                  key={kb.id}
                  className={cn(
                    'flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                    form.knowledge_base_ids.includes(kb.id)
                      ? 'border-primary bg-primary/5'
                      : 'border-border bg-background hover:border-muted-foreground/30'
                  )}
                >
                  <input
                    type="checkbox"
                    checked={form.knowledge_base_ids.includes(kb.id)}
                    onChange={() => toggleArrayItem('knowledge_base_ids', kb.id)}
                    className="h-4 w-4 rounded border-border accent-primary"
                  />
                  <div className="min-w-0">
                    <p className="text-sm text-foreground font-medium truncate">{kb.name}</p>
                    {kb.description && (
                      <p className="text-xs text-muted-foreground truncate">{kb.description}</p>
                    )}
                  </div>
                </label>
              ))}
            </div>
          )}
        </section>

        {/* Tools */}
        <section className="bg-card border border-border rounded-xl p-6 space-y-4">
          <h2 className="text-foreground font-semibold text-lg">Tools</h2>
          {toolsLoading ? (
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          ) : tools.length === 0 ? (
            <p className="text-muted-foreground text-sm">No tools available</p>
          ) : (
            <div className="space-y-2">
              {tools.map((tool) => (
                <label
                  key={tool.id}
                  className={cn(
                    'flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                    form.tool_ids.includes(tool.id)
                      ? 'border-primary bg-primary/5'
                      : 'border-border bg-background hover:border-muted-foreground/30'
                  )}
                >
                  <input
                    type="checkbox"
                    checked={form.tool_ids.includes(tool.id)}
                    onChange={() => toggleArrayItem('tool_ids', tool.id)}
                    className="h-4 w-4 rounded border-border accent-primary"
                  />
                  <div className="min-w-0">
                    <p className="text-sm text-foreground font-medium truncate">{tool.name}</p>
                    {tool.description && (
                      <p className="text-xs text-muted-foreground truncate">{tool.description}</p>
                    )}
                  </div>
                </label>
              ))}
            </div>
          )}
        </section>

        {/* Memory */}
        <section className="bg-card border border-border rounded-xl p-6 space-y-5">
          <h2 className="text-foreground font-semibold text-lg">Memory</h2>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-foreground font-medium">Enable Memory</p>
              <p className="text-xs text-muted-foreground">Allow the agent to remember past conversations</p>
            </div>
            <button
              type="button"
              onClick={() => updateNested('memory', 'enabled', !form.memory.enabled)}
              className={cn(
                'relative w-10 h-5 rounded-full transition-colors',
                form.memory.enabled ? 'bg-primary' : 'bg-muted'
              )}
            >
              <span
                className={cn(
                  'absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white transition-transform',
                  form.memory.enabled && 'translate-x-5'
                )}
              />
            </button>
          </div>
          {form.memory.enabled && (
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Window Size: {form.memory.window_size}
              </label>
              <input
                type="range"
                min={1}
                max={50}
                value={form.memory.window_size}
                onChange={(e) => updateNested('memory', 'window_size', Number(e.target.value))}
                className="w-full accent-primary"
              />
              <div className="flex justify-between text-[11px] text-muted-foreground mt-1">
                <span>1</span>
                <span>50</span>
              </div>
            </div>
          )}
        </section>

        {/* Guardrails */}
        <section className="bg-card border border-border rounded-xl p-6 space-y-5">
          <h2 className="text-foreground font-semibold text-lg">Guardrails</h2>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-foreground font-medium">Enable Guardrails</p>
              <p className="text-xs text-muted-foreground">Restrict agent outputs and token usage</p>
            </div>
            <button
              type="button"
              onClick={() => updateNested('guardrails', 'enabled', !form.guardrails.enabled)}
              className={cn(
                'relative w-10 h-5 rounded-full transition-colors',
                form.guardrails.enabled ? 'bg-primary' : 'bg-muted'
              )}
            >
              <span
                className={cn(
                  'absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white transition-transform',
                  form.guardrails.enabled && 'translate-x-5'
                )}
              />
            </button>
          </div>
          {form.guardrails.enabled && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Max Tokens</label>
                <input
                  type="number"
                  min={256}
                  max={128000}
                  value={form.guardrails.max_tokens}
                  onChange={(e) => updateNested('guardrails', 'max_tokens', Number(e.target.value))}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary font-mono"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Blocked Topics (comma-separated)</label>
                <input
                  type="text"
                  value={blockedTopicsInput}
                  onChange={(e) => setBlockedTopicsInput(e.target.value)}
                  placeholder="e.g. politics, violence, personal info"
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                />
              </div>
            </div>
          )}
        </section>

        {/* Actions */}
        <div className="flex gap-3 justify-end pb-8">
          <Link
            to="/agents"
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-secondary text-muted-foreground rounded-lg text-sm font-medium hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center gap-2 bg-primary text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save Changes
          </button>
        </div>
      </form>
    </div>
  );
}
