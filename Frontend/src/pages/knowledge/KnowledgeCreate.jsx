import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { knowledgeAPI } from '../../api/knowledge'
import { uploadAPI } from '../../api/upload'
import { useState, useRef } from 'react'
import { Loader2, FileText, Check, Upload, X } from 'lucide-react'
import { cn } from '../../lib/utils'

const chunkStrategies = [
  { value: 'recursive', label: 'Recursive' },
  { value: 'fixed_size', label: 'Fixed Size' },
  { value: 'sentence', label: 'Sentence' },
  { value: 'markdown', label: 'Markdown' },
]

const ACCEPTED_EXTENSIONS = '.pdf,.txt,.docx'
const ACCEPTED_TYPES = ['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']

export default function KnowledgeCreate() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const fileInputRef = useRef(null)
  const [form, setForm] = useState({
    name: '',
    description: '',
    selectedFiles: [],
    chunk_strategy: 'recursive',
    chunk_size: 1000,
    chunk_overlap: 200,
  })
  const [uploadingFile, setUploadingFile] = useState(null)
  const [uploadError, setUploadError] = useState(null)

  const { data: filesData, isLoading: filesLoading } = useQuery({
    queryKey: ['uploads'],
    queryFn: async () => {
      const res = await uploadAPI.list()
      return res.data
    },
  })
  const availableFiles = filesData?.files ?? []

  const uploadMutation = useMutation({
    mutationFn: (file) => uploadAPI.upload(file),
    onSuccess: async (res) => {
      const fileId = res.data.file_id
      setForm((prev) => ({
        ...prev,
        selectedFiles: [...prev.selectedFiles, fileId],
      }))
      setUploadingFile(null)
      setUploadError(null)
      await queryClient.invalidateQueries({ queryKey: ['uploads'] })
    },
    onError: (err) => {
      setUploadError(err.response?.data?.detail || 'Upload failed')
      setUploadingFile(null)
    },
  })

  const createMutation = useMutation({
    mutationFn: (data) => knowledgeAPI.create(data),
    onSuccess: () => navigate('/knowledge'),
  })

  const update = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))

  const toggleFile = (fileId) => {
    setForm((prev) => {
      const selected = prev.selectedFiles.includes(fileId)
        ? prev.selectedFiles.filter((id) => id !== fileId)
        : [...prev.selectedFiles, fileId]
      return { ...prev, selectedFiles: selected }
    })
  }

  const handleInlineUpload = (e) => {
    const f = e.target.files[0]
    if (!f) return
    if (f.size > 50 * 1024 * 1024) {
      setUploadError('File exceeds 50 MB limit.')
      return
    }
    setUploadError(null)
    setUploadingFile(f.name)
    uploadMutation.mutate(f)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const payload = {
      name: form.name,
      description: form.description,
      file_ids: form.selectedFiles,
      chunk_strategy: form.chunk_strategy,
      chunk_size: Number(form.chunk_size),
      chunk_overlap: Number(form.chunk_overlap),
    }
    createMutation.mutate(payload)
  }

  const extIcons = {
    '.pdf': 'text-red-400',
    '.txt': 'text-blue-400',
    '.docx': 'text-blue-300',
  }

  return (
    <div className="mx-auto max-w-2xl">
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
            placeholder="e.g. Company Documentation"
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

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-foreground">
              Select Files <span className="text-destructive">*</span>
            </label>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-secondary px-3 py-1.5 text-xs font-medium text-foreground hover:bg-secondary/80 transition-colors disabled:opacity-50"
            >
              {uploadMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Upload className="h-3.5 w-3.5" />
              )}
              Upload new file
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS}
              onChange={handleInlineUpload}
              className="hidden"
            />
          </div>

          {uploadingFile && (
            <div className="flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-xs text-primary">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Uploading {uploadingFile}...
            </div>
          )}

          {uploadError && (
            <div className="flex items-center justify-between rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              <span>{uploadError}</span>
              <button type="button" onClick={() => setUploadError(null)} className="shrink-0">
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          {filesLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : availableFiles.length === 0 ? (
            <div className="rounded-lg border border-border bg-secondary/30 px-4 py-8 text-center">
              <FileText className="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">No files available. Upload a file to get started.</p>
            </div>
          ) : (
            <div className="space-y-1 max-h-60 overflow-y-auto rounded-lg border border-border p-2">
              {availableFiles.map((f) => (
                <label
                  key={f.file_id}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2.5 cursor-pointer transition-colors',
                    form.selectedFiles.includes(f.file_id)
                      ? 'bg-primary/10 border border-primary/30'
                      : 'hover:bg-secondary border border-transparent'
                  )}
                >
                  <div className="relative flex h-5 w-5 shrink-0 items-center justify-center">
                    <input
                      type="checkbox"
                      checked={form.selectedFiles.includes(f.file_id)}
                      onChange={() => toggleFile(f.file_id)}
                      className="h-4 w-4 rounded border-border accent-primary"
                    />
                  </div>
                  <FileText className={cn('h-4 w-4 shrink-0', extIcons[f.extension] || 'text-muted-foreground')} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-foreground">{f.filename}</p>
                    <p className="text-xs text-muted-foreground">{f.size_mb} MB</p>
                  </div>
                  {form.selectedFiles.includes(f.file_id) && (
                    <Check className="h-4 w-4 shrink-0 text-primary" />
                  )}
                </label>
              ))}
            </div>
          )}
          {form.selectedFiles.length > 0 && (
            <p className="text-xs text-muted-foreground">
              {form.selectedFiles.length} file{form.selectedFiles.length > 1 ? 's' : ''} selected
            </p>
          )}
        </div>

        <div className="space-y-2">
          <label htmlFor="chunk_strategy" className="text-sm font-medium text-foreground">
            Chunk Strategy
          </label>
          <select
            id="chunk_strategy"
            value={form.chunk_strategy}
            onChange={(e) => update('chunk_strategy', e.target.value)}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {chunkStrategies.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label htmlFor="chunk_size" className="text-sm font-medium text-foreground">
              Chunk Size
            </label>
            <input
              id="chunk_size"
              type="number"
              min={100}
              max={10000}
              value={form.chunk_size}
              onChange={(e) => update('chunk_size', e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <p className="text-xs text-muted-foreground">100 – 10,000</p>
          </div>
          <div className="space-y-2">
            <label htmlFor="chunk_overlap" className="text-sm font-medium text-foreground">
              Chunk Overlap
            </label>
            <input
              id="chunk_overlap"
              type="number"
              min={0}
              max={5000}
              value={form.chunk_overlap}
              onChange={(e) => update('chunk_overlap', e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <p className="text-xs text-muted-foreground">0 – 5,000</p>
          </div>
        </div>

        {createMutation.isError && (
          <div className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {createMutation.error?.response?.data?.detail || 'Failed to create knowledge base.'}
          </div>
        )}

        <div className="flex justify-end gap-3 pb-8">
          <button
            type="button"
            onClick={() => navigate('/knowledge')}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createMutation.isPending || form.selectedFiles.length === 0}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Create Knowledge Base
          </button>
        </div>
      </form>
    </div>
  )
}
