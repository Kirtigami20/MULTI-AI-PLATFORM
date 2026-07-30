import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { toolsAPI } from '../../api/tools'
import { useState, useEffect } from 'react'
import { Loader2, Plus, Trash2 } from 'lucide-react'

const httpMethods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
const paramTypes = ['string', 'number', 'integer', 'boolean', 'array', 'object']
const paramLocations = ['query', 'body', 'path', 'header']
const authTypes = [
  { value: 'none', label: 'None' },
  { value: 'api_key', label: 'API Key' },
  { value: 'bearer', label: 'Bearer Token' },
  { value: 'basic', label: 'Basic Auth' },
]

const emptyParam = () => ({
  id: Date.now() + Math.random(),
  name: '',
  type: 'string',
  description: '',
  required: true,
  location: 'body',
})

const emptyAuth = () => ({
  type: 'none',
  token: '',
  header: 'X-API-Key',
  location: 'header',
  username: '',
})

export default function ToolEdit() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState(null)

  const { data: tool, isLoading: toolLoading, error: toolError } = useQuery({
    queryKey: ['tool', id],
    queryFn: () => toolsAPI.get(id).then((r) => r.data),
  })

  useEffect(() => {
    if (tool) {
      const config = tool.config || {}
      const headers = config.headers
        ? (typeof config.headers === 'string' ? config.headers : JSON.stringify(config.headers))
        : ''
      const parameters = (config.parameters || []).map((p, i) => ({
        ...p,
        id: Date.now() + i,
      }))
      const auth = config.auth || emptyAuth()

      setForm({
        name: tool.name || '',
        description: tool.description || '',
        tool_type: tool.tool_type || 'api',
        config: {
          url: config.url || '',
          method: config.method || 'POST',
          headers,
          parameters: parameters.length > 0 ? parameters : [emptyParam()],
          body_template: config.body_template || '',
          auth,
        },
      })
    }
  }, [tool])

  const updateMutation = useMutation({
    mutationFn: (data) => toolsAPI.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools'] })
      queryClient.invalidateQueries({ queryKey: ['tool', id] })
      navigate('/tools')
    },
  })

  const update = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))

  const updateConfig = (key, value) =>
    setForm((prev) => ({ ...prev, config: { ...prev.config, [key]: value } }))

  const updateParam = (paramId, key, value) => {
    setForm((prev) => ({
      ...prev,
      config: {
        ...prev.config,
        parameters: prev.config.parameters.map((p) =>
          p.id === paramId ? { ...p, [key]: value } : p
        ),
      },
    }))
  }

  const addParam = () => {
    setForm((prev) => ({
      ...prev,
      config: {
        ...prev.config,
        parameters: [...prev.config.parameters, emptyParam()],
      },
    }))
  }

  const removeParam = (paramId) => {
    setForm((prev) => ({
      ...prev,
      config: {
        ...prev.config,
        parameters: prev.config.parameters.filter((p) => p.id !== paramId),
      },
    }))
  }

  const updateAuth = (key, value) => {
    setForm((prev) => ({
      ...prev,
      config: {
        ...prev.config,
        auth: { ...prev.config.auth, [key]: value },
      },
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const payload = {
      name: form.name,
      description: form.description,
    }

    if (form.tool_type === 'api') {
      let headers = {}
      try {
        headers = form.config.headers ? JSON.parse(form.config.headers) : {}
      } catch {
        updateMutation.error = { message: 'Invalid JSON in headers field.' }
        return
      }

      const parameters = form.config.parameters
        .filter((p) => p.name.trim())
        .map(({ id: _id, ...rest }) => rest)

      const auth = form.config.auth.type !== 'none' ? { ...form.config.auth } : { type: 'none' }

      payload.config = {
        url: form.config.url,
        method: form.config.method,
        headers,
        parameters,
        body_template: form.config.body_template || null,
        auth,
      }
    }

    updateMutation.mutate(payload)
  }

  if (toolLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (toolError || !form) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <p className="text-destructive text-sm">Failed to load tool data.</p>
        <Link to="/tools" className="text-primary text-sm hover:underline">
          Back to tools
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-2">
          <label htmlFor="name" className="text-sm font-medium text-foreground">
            Name <span className="text-destructive">*</span>
          </label>
          <input
            id="name"
            type="text"
            required
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
            placeholder="e.g. Weather API"
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="description" className="text-sm font-medium text-foreground">
            Description
          </label>
          <textarea
            id="description"
            rows={3}
            value={form.description}
            onChange={(e) => update('description', e.target.value)}
            placeholder="Optional description"
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
          />
        </div>

        <div className="space-y-3">
          <label className="text-sm font-medium text-foreground">Tool Type</label>
          <div className="flex gap-4">
            {['builtin', 'api'].map((type) => (
              <label
                key={type}
                className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm cursor-pointer transition-colors ${
                  form.tool_type === type
                    ? 'border-primary bg-primary/10 text-foreground'
                    : 'border-border text-muted-foreground hover:border-muted-foreground/50'
                }`}
              >
                <input
                  type="radio"
                  name="tool_type"
                  value={type}
                  checked={form.tool_type === type}
                  onChange={(e) => update('tool_type', e.target.value)}
                  className="sr-only"
                />
                {type === 'builtin' ? 'Built-in' : 'API'}
              </label>
            ))}
          </div>
        </div>

        {form.tool_type === 'api' && (
          <>
            <div className="space-y-4 rounded-lg border border-border p-4">
              <h3 className="text-sm font-medium text-foreground">Endpoint</h3>

              <div className="space-y-2">
                <label htmlFor="url" className="text-sm font-medium text-foreground">
                  URL <span className="text-destructive">*</span>
                </label>
                <input
                  id="url"
                  type="url"
                  required={form.tool_type === 'api'}
                  value={form.config.url}
                  onChange={(e) => updateConfig('url', e.target.value)}
                  placeholder="https://api.example.com/endpoint"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              <div className="flex gap-4">
                <div className="space-y-2 flex-1">
                  <label htmlFor="method" className="text-sm font-medium text-foreground">
                    Method
                  </label>
                  <select
                    id="method"
                    value={form.config.method}
                    onChange={(e) => updateConfig('method', e.target.value)}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  >
                    {httpMethods.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2 flex-1">
                  <label htmlFor="headers" className="text-sm font-medium text-foreground">
                    Static Headers (JSON)
                  </label>
                  <input
                    id="headers"
                    type="text"
                    value={form.config.headers}
                    onChange={(e) => updateConfig('headers', e.target.value)}
                    placeholder='{"X-Custom": "value"}'
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-4 rounded-lg border border-border p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-foreground">Parameters</h3>
                <button
                  type="button"
                  onClick={addParam}
                  className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80 transition-colors"
                >
                  <Plus className="h-3 w-3" />
                  Add
                </button>
              </div>

              {form.config.parameters.length === 0 ? (
                <p className="text-xs text-muted-foreground">No parameters defined. LLM will send raw input.</p>
              ) : (
                <div className="space-y-3">
                  {form.config.parameters.map((param) => (
                    <div
                      key={param.id}
                      className="flex flex-wrap items-start gap-2 rounded-lg border border-border p-3"
                    >
                      <input
                        type="text"
                        value={param.name}
                        onChange={(e) => updateParam(param.id, 'name', e.target.value)}
                        placeholder="name"
                        className="w-28 rounded-md border border-border bg-background px-2 py-1.5 text-xs font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                      />

                      <select
                        value={param.type}
                        onChange={(e) => updateParam(param.id, 'type', e.target.value)}
                        className="w-24 rounded-md border border-border bg-background px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                      >
                        {paramTypes.map((t) => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>

                      <select
                        value={param.location}
                        onChange={(e) => updateParam(param.id, 'location', e.target.value)}
                        className="w-20 rounded-md border border-border bg-background px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                      >
                        {paramLocations.map((l) => (
                          <option key={l} value={l}>{l}</option>
                        ))}
                      </select>

                      <input
                        type="text"
                        value={param.description}
                        onChange={(e) => updateParam(param.id, 'description', e.target.value)}
                        placeholder="description"
                        className="flex-1 min-w-[100px] rounded-md border border-border bg-background px-2 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                      />

                      <label className="flex items-center gap-1 text-xs text-muted-foreground cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={param.required}
                          onChange={(e) => updateParam(param.id, 'required', e.target.checked)}
                          className="h-3 w-3 rounded border-border accent-primary"
                        />
                        req
                      </label>

                      <button
                        type="button"
                        onClick={() => removeParam(param.id)}
                        className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="space-y-2 rounded-lg border border-border p-4">
              <h3 className="text-sm font-medium text-foreground">Body Template</h3>
              <p className="text-xs text-muted-foreground">
                Use {'{param_name}'} to reference parameters. Leave empty to send raw JSON from LLM.
              </p>
              <textarea
                rows={4}
                value={form.config.body_template}
                onChange={(e) => updateConfig('body_template', e.target.value)}
                placeholder='{"query": "{query}", "limit": {limit}}'
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              />
            </div>

            <div className="space-y-4 rounded-lg border border-border p-4">
              <h3 className="text-sm font-medium text-foreground">Authentication</h3>

              <div className="flex flex-wrap gap-3">
                {authTypes.map((a) => (
                  <label
                    key={a.value}
                    className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs cursor-pointer transition-colors ${
                      form.config.auth.type === a.value
                        ? 'border-primary bg-primary/10 text-foreground'
                        : 'border-border text-muted-foreground hover:border-muted-foreground/50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="auth_type"
                      value={a.value}
                      checked={form.config.auth.type === a.value}
                      onChange={(e) => updateAuth('type', e.target.value)}
                      className="sr-only"
                    />
                    {a.label}
                  </label>
                ))}
              </div>

              {form.config.auth.type === 'bearer' && (
                <div className="space-y-2">
                  <label className="text-xs font-medium text-foreground">Token</label>
                  <input
                    type="text"
                    value={form.config.auth.token}
                    onChange={(e) => updateAuth('token', e.target.value)}
                    placeholder="Bearer token"
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>
              )}

              {form.config.auth.type === 'api_key' && (
                <div className="space-y-3">
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-foreground">API Key Location</label>
                    <div className="flex gap-3">
                      {['header', 'query', 'body'].map((loc) => (
                        <label
                          key={loc}
                          className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs cursor-pointer transition-colors ${
                            form.config.auth.location === loc
                              ? 'border-primary bg-primary/10 text-foreground'
                              : 'border-border text-muted-foreground hover:border-muted-foreground/50'
                          }`}
                        >
                          <input
                            type="radio"
                            name="auth_location"
                            value={loc}
                            checked={form.config.auth.location === loc}
                            onChange={(e) => updateAuth('location', e.target.value)}
                            className="sr-only"
                          />
                          {loc === 'header' ? 'Header' : loc === 'query' ? 'Query' : 'Body'}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="space-y-2 flex-1">
                      <label className="text-xs font-medium text-foreground">Key Name</label>
                      <input
                        type="text"
                        value={form.config.auth.header}
                        onChange={(e) => updateAuth('header', e.target.value)}
                        placeholder="api_token"
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                    </div>
                    <div className="space-y-2 flex-1">
                      <label className="text-xs font-medium text-foreground">Key Value</label>
                      <input
                        type="password"
                        value={form.config.auth.token}
                        onChange={(e) => updateAuth('token', e.target.value)}
                        placeholder="API key value"
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                    </div>
                  </div>
                </div>
              )}

              {form.config.auth.type === 'basic' && (
                <div className="flex gap-3">
                  <div className="space-y-2 flex-1">
                    <label className="text-xs font-medium text-foreground">Username</label>
                    <input
                      type="text"
                      value={form.config.auth.username}
                      onChange={(e) => updateAuth('username', e.target.value)}
                      placeholder="username"
                      className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                  <div className="space-y-2 flex-1">
                    <label className="text-xs font-medium text-foreground">Password / Token</label>
                    <input
                      type="password"
                      value={form.config.auth.token}
                      onChange={(e) => updateAuth('token', e.target.value)}
                      placeholder="password"
                      className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {updateMutation.isError && (
          <div className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {updateMutation.error?.response?.data?.detail || 'Failed to update tool.'}
          </div>
        )}

        <div className="flex justify-end gap-3">
          <Link
            to="/tools"
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={updateMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {updateMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Save Changes
          </button>
        </div>
      </form>
    </div>
  )
}
