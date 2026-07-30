import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { toolsAPI } from '../../api/tools'
import { Wrench, Trash2, Plus, Globe, Settings, Loader2, Pencil } from 'lucide-react'
import { cn } from '../../lib/utils'
import { useState } from 'react'

const typeConfig = {
  builtin: { label: 'Built-in', className: 'bg-primary/15 text-primary', icon: Settings },
  api: { label: 'API', className: 'bg-success/15 text-success', icon: Globe },
}

export default function ToolList() {
  const queryClient = useQueryClient()
  const [deleteId, setDeleteId] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['tools'],
    queryFn: async () => {
      const res = await toolsAPI.list()
      return res.data
    },
  })
  const tools = data?.tools ?? []

  const deleteMutation = useMutation({
    mutationFn: (id) => toolsAPI.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools'] })
      setDeleteId(null)
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {tools.length} tool{tools.length !== 1 && 's'}
        </p>
        <Link
          to="/tools/new"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Create Tool
        </Link>
      </div>

      {tools.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-20 text-center">
          <Wrench className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium text-foreground">No tools</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Create your first tool to get started.
          </p>
          <Link
            to="/tools/new"
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create Tool
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tools.map((tool) => {
            const type = typeConfig[tool.tool_type] || typeConfig.builtin
            const TypeIcon = type.icon
            return (
              <div
                key={tool.id}
                className="group relative overflow-hidden rounded-xl border border-border bg-background p-5 transition-colors hover:border-muted-foreground/30"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-secondary">
                      <TypeIcon className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate font-medium text-foreground">{tool.name}</h3>
                      {tool.description && (
                        <p className="mt-0.5 truncate text-sm text-muted-foreground">
                          {tool.description}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <Link
                      to={`/tools/${tool.id}/edit`}
                      className="rounded-md p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-primary/10 hover:text-primary group-hover:opacity-100"
                    >
                      <Pencil className="h-4 w-4" />
                    </Link>
                    <button
                      onClick={() => setDeleteId(tool.id)}
                      className="rounded-md p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div className="mt-4 flex min-w-0 flex-wrap items-center gap-2 text-xs">
                  <span className={cn('inline-flex shrink-0 items-center gap-1 rounded-full px-2.5 py-0.5 font-medium', type.className)}>
                    <TypeIcon className="h-3 w-3" />
                    {type.label}
                  </span>
                  {tool.tool_type === 'api' && tool.config?.url && (
                    <span className="min-w-0 truncate text-muted-foreground">
                      {tool.config.url}
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="mx-4 w-full max-w-sm rounded-xl border border-border bg-background p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-foreground">Delete Tool?</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              This action cannot be undone. The tool will be permanently removed.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setDeleteId(null)}
                className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteId)}
                disabled={deleteMutation.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:bg-destructive/90 transition-colors disabled:opacity-50"
              >
                {deleteMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
