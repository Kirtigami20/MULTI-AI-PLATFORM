import { useState, useRef, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { uploadAPI } from '../api/upload'
import { Upload, FileText, CheckCircle, AlertCircle, Loader2, X } from 'lucide-react'
import { cn } from '../lib/utils'

const ACCEPTED_TYPES = ['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
const ACCEPTED_EXTENSIONS = '.pdf,.txt,.docx'
const MAX_SIZE = 50 * 1024 * 1024

export default function UploadPage() {
  const [dragOver, setDragOver] = useState(false)
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const { data: uploadedData, refetch } = useQuery({
    queryKey: ['uploads'],
    queryFn: async () => {
      const res = await uploadAPI.list()
      return res.data
    },
  })
  const uploadedFiles = uploadedData?.files ?? []

  const validateFile = (f) => {
    if (f.size > MAX_SIZE) return 'File exceeds 50 MB limit.'
    if (!ACCEPTED_TYPES.includes(f.type) && !ACCEPTED_EXTENSIONS.split(',').some((ext) => f.name.endsWith(ext))) {
      return 'Unsupported file type. Use PDF, TXT, or DOCX.'
    }
    return null
  }

  const handleFile = useCallback((f) => {
    setError(null)
    setResult(null)
    const err = validateFile(f)
    if (err) {
      setError(err)
      return
    }
    setFile(f)
  }, [])

  const onDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  const onDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  const onDragLeave = () => setDragOver(false)

  const onInputChange = (e) => {
    const f = e.target.files[0]
    if (f) handleFile(f)
  }

  const upload = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    setResult(null)
    try {
      const res = await uploadAPI.upload(file)
      const data = res.data
      setResult(data)
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
      refetch()
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const clearFile = () => {
    setFile(null)
    setError(null)
    setResult(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const formatSize = (mb) => {
    if (mb < 1) return Math.round(mb * 1024) + ' KB'
    return mb + ' MB'
  }

  const extIcons = {
    '.pdf': 'text-red-400',
    '.txt': 'text-blue-400',
    '.docx': 'text-blue-300',
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={() => inputRef.current?.click()}
        className={cn(
          'relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed py-12 text-center transition-colors',
          dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-muted-foreground/40',
        )}
      >
        <Upload className="mb-3 h-10 w-10 text-muted-foreground" />
        <p className="text-sm font-medium text-foreground">
          Drag & drop a file here, or click to browse
        </p>
        <p className="mt-1 text-xs text-muted-foreground">PDF, TXT, DOCX — max 50 MB</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS}
          onChange={onInputChange}
          className="hidden"
        />
      </div>

      {file && (
        <div className="flex items-center justify-between rounded-lg border border-border bg-secondary/50 px-4 py-3">
          <div className="flex items-center gap-3 min-w-0">
            <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">{file.name}</p>
              <p className="text-xs text-muted-foreground">{formatSize(file.size / (1024 * 1024))}</p>
            </div>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation()
              clearFile()
            }}
            className="ml-3 shrink-0 rounded-md p-1 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <button
        onClick={upload}
        disabled={!file || uploading}
        className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {uploading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Uploading...
          </>
        ) : (
          <>
            <Upload className="h-4 w-4" />
            Upload
          </>
        )}
      </button>

      {result && (
        <div className="flex items-start gap-3 rounded-lg bg-success/10 px-4 py-3 text-sm text-success">
          <CheckCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-medium">Upload successful</p>
            <p className="mt-0.5 text-xs text-success/80">{result.filename}</p>
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-3 rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {uploadedFiles.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">Uploaded Files</h3>
          <div className="space-y-2">
            {uploadedFiles.map((item) => (
              <div
                key={item.file_id}
                className="flex items-center justify-between rounded-lg border border-border px-4 py-2.5"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <FileText className={cn('h-4 w-4 shrink-0', extIcons[item.extension] || 'text-muted-foreground')} />
                  <div className="min-w-0">
                    <span className="truncate text-sm text-foreground">{item.filename}</span>
                    <span className="ml-2 text-xs text-muted-foreground">{formatSize(item.size_mb)}</span>
                  </div>
                </div>
                <CheckCircle className="h-4 w-4 shrink-0 text-success" />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
