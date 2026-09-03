import { useState, useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { Key, Plus, Trash2, Copy, Check, Eye, EyeOff, AlertTriangle, X } from 'lucide-react'
import { apiKeysAPI } from '../api/client'

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={handleCopy} className="btn btn-outline btn-sm" title="Copy">
      {copied ? <Check size={12} style={{ color: 'var(--color-emerald)' }} /> : <Copy size={12} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function CreateKeyModal({ onClose, onCreate }) {
  const ref = useRef(null)
  const { register, handleSubmit, formState: { errors } } = useForm()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    gsap.fromTo(ref.current,
      { opacity: 0, scale: 0.95, y: -10 },
      { opacity: 1, scale: 1, y: 0, duration: 0.3, ease: 'power3.out' }
    )
  }, [])

  const close = () => {
    gsap.to(ref.current, { opacity: 0, scale: 0.95, duration: 0.2, onComplete: onClose })
  }

  const onSubmit = async (data) => {
    setLoading(true)
    try {
      const res = await apiKeysAPI.create({
        label: data.label,
        expires_in_days: data.expires_in_days ? parseInt(data.expires_in_days) : undefined,
      })
      onCreate(res.data)
      close()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create key')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}>
      <div ref={ref} className="card animated-border w-full max-w-md mx-4" style={{ opacity: 0 }}>
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="text-base font-semibold" style={{ color: 'var(--color-text)' }}>Create API Key</div>
            <div className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>For server-to-server webhook authentication</div>
          </div>
          <button onClick={close} className="btn btn-outline btn-sm p-1.5"><X size={14} /></button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>Key Label</label>
            <input
              className="input"
              placeholder="e.g. Production Webhook Server"
              {...register('label', { required: true, minLength: 1 })}
            />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>
              Expires In (days) <span style={{ color: 'var(--color-text-subtle)' }}>— optional</span>
            </label>
            <input
              className="input"
              type="number"
              min="1"
              max="365"
              placeholder="Leave blank for no expiry"
              {...register('expires_in_days')}
            />
          </div>
          <button type="submit" className="btn btn-primary w-full" disabled={loading}>
            {loading ? <div className="spinner" /> : <><Key size={14} /> Generate Key</>}
          </button>
        </form>
      </div>
    </div>
  )
}

function RevealModal({ keyData, onClose }) {
  const ref = useRef(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    gsap.fromTo(ref.current,
      { opacity: 0, scale: 0.95 },
      { opacity: 1, scale: 1, duration: 0.3, ease: 'power3.out' }
    )
  }, [])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}>
      <div ref={ref} className="card animated-border w-full max-w-lg mx-4" style={{ opacity: 0 }}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'var(--color-emerald-dim)' }}>
            <Key size={18} style={{ color: 'var(--color-emerald)' }} />
          </div>
          <div>
            <div className="text-base font-semibold" style={{ color: 'var(--color-text)' }}>Key Created</div>
            <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{keyData.label}</div>
          </div>
        </div>

        <div
          className="rounded-xl p-3 mb-4"
          style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)' }}
        >
          <div className="flex items-center gap-2 text-xs mb-1" style={{ color: 'var(--color-amber)' }}>
            <AlertTriangle size={11} />
            <strong>Copy this key now — it will never be shown again.</strong>
          </div>
          <div className="text-xs" style={{ color: 'var(--color-amber)' }}>
            Store it securely in your environment variables or secrets manager.
          </div>
        </div>

        <div className="rounded-lg p-3 mb-4 flex items-center gap-2" style={{ background: 'var(--color-surface-2)', border: '1px solid var(--color-border)' }}>
          <code className="flex-1 text-xs font-mono break-all" style={{ color: 'var(--color-primary-hover)' }}>
            {visible ? keyData.raw_key : '•'.repeat(40)}
          </code>
          <button onClick={() => setVisible(!visible)} className="flex-shrink-0 btn btn-outline btn-sm p-1.5">
            {visible ? <EyeOff size={12} /> : <Eye size={12} />}
          </button>
          <CopyButton text={keyData.raw_key} />
        </div>

        <button onClick={onClose} className="btn btn-primary w-full">
          Done — I've saved the key
        </button>
      </div>
    </div>
  )
}

export default function ApiKeysPage() {
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [revealKey, setRevealKey] = useState(null)
  const listRef = useRef(null)

  const fetchKeys = async () => {
    try {
      const res = await apiKeysAPI.list()
      setKeys(res.data)
    } catch { toast.error('Failed to load API keys') }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchKeys() }, [])

  useEffect(() => {
    if (!loading && listRef.current) {
      gsap.fromTo(listRef.current.querySelectorAll('tr'),
        { opacity: 0, x: -10 },
        { opacity: 1, x: 0, duration: 0.3, stagger: 0.07, ease: 'power2.out', delay: 0.1 }
      )
    }
  }, [loading])

  const handleCreated = (data) => {
    setRevealKey(data)
    fetchKeys()
    toast.success('API key created!')
  }

  const handleRevoke = async (keyId, label) => {
    if (!window.confirm(`Revoke key "${label}"? This cannot be undone.`)) return
    try {
      await apiKeysAPI.revoke(keyId)
      toast.success('Key revoked.')
      fetchKeys()
    } catch { toast.error('Failed to revoke key') }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {showCreate && <CreateKeyModal onClose={() => setShowCreate(false)} onCreate={handleCreated} />}
      {revealKey && <RevealModal keyData={revealKey} onClose={() => setRevealKey(null)} />}

      {/* Header */}
      <div className="flex items-center justify-between mb-7">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>API Keys</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
            Programmatic access for server-to-server webhook integration
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={14} /> Create Key
        </button>
      </div>

      {/* Usage hint */}
      <div
        className="rounded-xl px-4 py-3 mb-5 text-xs"
        style={{ background: 'var(--color-primary-glow)', border: '1px solid rgba(99,102,241,0.25)' }}
      >
        <div className="font-semibold mb-0.5" style={{ color: 'var(--color-primary-hover)' }}>Using API Keys</div>
        <div style={{ color: 'var(--color-text-muted)' }}>
          Pass the key as <code className="font-mono" style={{ color: 'var(--color-primary-hover)' }}>X-API-Key: rzr_live_...</code> header in your webhook requests.
          Alternatively, use Bearer JWT tokens from <code className="font-mono">POST /auth/login</code>.
        </div>
      </div>

      {/* Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div className="py-16 text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
            <div className="spinner mx-auto mb-3" />
            Loading...
          </div>
        ) : keys.length === 0 ? (
          <div className="py-16 text-center">
            <Key size={32} className="mx-auto mb-3" style={{ color: 'var(--color-border-2)' }} />
            <div className="text-sm font-medium mb-1" style={{ color: 'var(--color-text)' }}>No API keys yet</div>
            <div className="text-xs mb-4" style={{ color: 'var(--color-text-muted)' }}>Create one to enable server-to-server authentication</div>
            <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}>
              <Plus size={13} /> Create your first key
            </button>
          </div>
        ) : (
          <table className="table-auto w-full" ref={listRef}>
            <thead>
              <tr>
                <th>Label</th>
                <th>Key Prefix</th>
                <th>Status</th>
                <th>Last Used</th>
                <th>Expires</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id}>
                  <td className="font-medium">{k.label}</td>
                  <td>
                    <code className="text-xs font-mono px-2 py-1 rounded" style={{ background: 'var(--color-surface-2)', color: 'var(--color-primary-hover)' }}>
                      {k.prefix}
                    </code>
                  </td>
                  <td>
                    <span className={`badge ${k.is_active ? 'badge-emerald' : 'badge-red'}`}>
                      {k.is_active ? 'Active' : 'Revoked'}
                    </span>
                  </td>
                  <td style={{ color: 'var(--color-text-muted)' }}>
                    {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString('en-IN') : 'Never'}
                  </td>
                  <td style={{ color: 'var(--color-text-muted)' }}>
                    {k.expires_at ? new Date(k.expires_at).toLocaleDateString('en-IN') : '—'}
                  </td>
                  <td className="text-right">
                    {k.is_active && (
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handleRevoke(k.id, k.label)}
                      >
                        <Trash2 size={12} /> Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
