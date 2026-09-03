import { useRef, useState, useEffect } from 'react'
import { gsap } from 'gsap'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { Zap, CheckCircle, Clock, XCircle, ExternalLink, RotateCcw, ChevronDown } from 'lucide-react'
import { recoveryAPI } from '../api/client'
import confetti from 'canvas-confetti'

const ERROR_CODES = [
  'BAD_REQUEST_PAYMENT_TIMED_OUT',
  'BAD_REQUEST_PAYMENT_CARD_INSUFFICIENT_FUNDS',
  'BAD_REQUEST_PAYMENT_OTP_EXPIRED',
  'BAD_REQUEST_PAYMENT_POSSIBLE_FRAUD',
  'GATEWAY_ERROR_BANK_SYSTEM_ERROR',
  'BAD_REQUEST_PAYMENT_CARD_HOLDER_AUTHENTICATION_FAILED',
  'BAD_REQUEST_PAYMENT_CANCELLED',
]

const PRESETS = [
  {
    label: 'OTP Timeout — VIP',
    data: { order_id: 'order_DEMO_001', payment_id: 'pay_demo001', amount: 250000, error_code: 'BAD_REQUEST_PAYMENT_OTP_EXPIRED', error_description: 'OTP expired', customer_name: 'Priya Sharma', customer_phone: '+919876543210', customer_tier: 'VIP', attempts_made: 0 },
  },
  {
    label: 'Insufficient Funds',
    data: { order_id: 'order_DEMO_002', payment_id: 'pay_demo002', amount: 73500, error_code: 'BAD_REQUEST_PAYMENT_CARD_INSUFFICIENT_FUNDS', error_description: 'Card declined', customer_name: 'Rahul Mehra', customer_phone: '+919876543211', customer_tier: 'STANDARD', attempts_made: 0 },
  },
  {
    label: 'Bank Outage',
    data: { order_id: 'order_DEMO_003', payment_id: 'pay_demo003', amount: 999900, error_code: 'GATEWAY_ERROR_BANK_SYSTEM_ERROR', error_description: 'Bank 503', customer_name: 'Anjali Patel', customer_phone: '+919876543212', customer_tier: 'STANDARD', attempts_made: 0 },
  },
  {
    label: 'Fraud Flag (Halt)',
    data: { order_id: 'order_DEMO_004', payment_id: 'pay_demo004', amount: 450000, error_code: 'BAD_REQUEST_PAYMENT_POSSIBLE_FRAUD', error_description: 'Fraud flag', customer_name: 'Unknown User', customer_phone: '+919876543213', customer_tier: 'STANDARD', attempts_made: 0 },
  },
]

const statusStyle = {
  RECOVERED_PENDING_PAYMENT: { color: 'var(--color-emerald)', icon: CheckCircle, badge: 'badge-emerald', label: 'Recovered' },
  SCHEDULED_RETRY: { color: 'var(--color-amber)', icon: Clock, badge: 'badge-amber', label: 'Retry Queued' },
  ABORTED: { color: 'var(--color-red)', icon: XCircle, badge: 'badge-red', label: 'Aborted' },
}

export default function WebhookPage() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const resultRef = useRef(null)
  const formRef = useRef(null)
  const { register, handleSubmit, reset, setValue } = useForm({
    defaultValues: {
      order_id: `order_TEST_${Date.now().toString(36).toUpperCase()}`,
      payment_id: `pay_${Math.random().toString(36).slice(2, 10)}`,
      amount: 250000,
      currency: 'INR',
      error_code: 'BAD_REQUEST_PAYMENT_OTP_EXPIRED',
      error_description: 'OTP expired during authentication',
      customer_name: 'Arjun Demo',
      customer_phone: '+919876543210',
      customer_tier: 'STANDARD',
      attempts_made: 0,
    },
  })

  const applyPreset = (preset) => {
    Object.entries(preset.data).forEach(([k, v]) => setValue(k, v))
    setResult(null)
  }

  const onSubmit = async (data) => {
    setLoading(true)
    setResult(null)
    try {
      const payload = { ...data, amount: parseInt(data.amount), attempts_made: parseInt(data.attempts_made) }
      const res = await recoveryAPI.fireWebhook(payload)
      setResult(res.data)

      // GSAP result reveal
      if (resultRef.current) {
        gsap.fromTo(resultRef.current,
          { opacity: 0, y: 20, scale: 0.97 },
          { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: 'power3.out' }
        )
      }

      // Confetti for recovered payments
      if (res.data.status === 'RECOVERED_PENDING_PAYMENT') {
        confetti({ particleCount: 80, spread: 60, origin: { y: 0.6 }, colors: ['#6366f1', '#10b981', '#06b6d4'] })
      }

      toast.success(`Recovery strategy: ${res.data.ai_strategy}`)
    } catch (err) {
      const msg = err.response?.data?.detail
      if (err.response?.status === 409) {
        toast.error('Duplicate order ID — this order was already processed.')
      } else {
        toast.error(typeof msg === 'string' ? msg : 'Webhook failed.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-7">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
          Webhook Tester
        </h1>
        <p className="text-sm mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
          Fire a <code className="font-mono text-xs px-1.5 py-0.5 rounded" style={{ background: 'var(--color-surface-2)', color: 'var(--color-primary-hover)' }}>payment.failed</code> event and watch the AI recovery engine respond in real-time.
        </p>
      </div>

      {/* Presets */}
      <div className="flex flex-wrap gap-2 mb-5">
        <span className="text-xs self-center" style={{ color: 'var(--color-text-muted)' }}>Quick scenarios:</span>
        {PRESETS.map((p) => (
          <button key={p.label} className="btn btn-outline btn-sm" onClick={() => applyPreset(p)}>
            {p.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Form */}
        <div ref={formRef} className="card">
          <div className="flex items-center justify-between mb-5">
            <div className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
              Event Payload
            </div>
            <button
              className="btn btn-outline btn-sm"
              onClick={() => {
                reset()
                setResult(null)
                setValue('order_id', `order_TEST_${Date.now().toString(36).toUpperCase()}`)
                setValue('payment_id', `pay_${Math.random().toString(36).slice(2, 10)}`)
              }}
            >
              <RotateCcw size={11} />
              Reset
            </button>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>Order ID</label>
                <input className="input" {...register('order_id', { required: true })} />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>Payment ID</label>
                <input className="input" {...register('payment_id', { required: true })} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>Amount (paise)</label>
                <input className="input" type="number" {...register('amount', { required: true, min: 1 })} />
                <div className="text-[10px] mt-0.5" style={{ color: 'var(--color-text-muted)' }}>100 paise = ₹1</div>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>Attempts Made</label>
                <input className="input" type="number" min="0" max="5" {...register('attempts_made')} />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>Error Code</label>
              <div className="relative">
                <select className="input appearance-none pr-8" {...register('error_code', { required: true })}>
                  {ERROR_CODES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <ChevronDown size={13} className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'var(--color-text-muted)' }} />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>Error Description</label>
              <input className="input" {...register('error_description')} />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>Customer Name</label>
                <input className="input" {...register('customer_name', { required: true })} />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>Phone</label>
                <input className="input" {...register('customer_phone', { required: true })} />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>Customer Tier</label>
              <div className="relative">
                <select className="input appearance-none pr-8" {...register('customer_tier')}>
                  <option value="STANDARD">STANDARD</option>
                  <option value="VIP">VIP</option>
                  <option value="REPEAT_DROPOFF">REPEAT_DROPOFF</option>
                </select>
                <ChevronDown size={13} className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'var(--color-text-muted)' }} />
              </div>
            </div>

            <button type="submit" className="btn btn-primary w-full mt-2" disabled={loading}>
              {loading ? <div className="spinner" /> : <><Zap size={14} /> Fire Webhook</>}
            </button>
          </form>
        </div>

        {/* Result */}
        <div>
          {!result && !loading && (
            <div
              className="card h-full flex flex-col items-center justify-center text-center"
              style={{ minHeight: 300 }}
            >
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
                style={{ background: 'var(--color-primary-glow)' }}
              >
                <Zap size={24} style={{ color: 'var(--color-primary-hover)' }} />
              </div>
              <div className="text-sm font-medium mb-1" style={{ color: 'var(--color-text)' }}>
                Waiting for event
              </div>
              <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Fill the form and fire a webhook to see the AI decision
              </div>
            </div>
          )}

          {loading && (
            <div className="card h-full flex flex-col items-center justify-center" style={{ minHeight: 300 }}>
              <div className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
              <div className="text-sm mt-4" style={{ color: 'var(--color-text-muted)' }}>
                AI engine processing...
              </div>
            </div>
          )}

          {result && !loading && (() => {
            const s = statusStyle[result.status] || statusStyle.ABORTED
            const Icon = s.icon
            return (
              <div ref={resultRef} className="card" style={{ opacity: 0 }}>
                {/* Status */}
                <div className="flex items-center gap-3 mb-5">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center"
                    style={{ background: `${s.color}22` }}
                  >
                    <Icon size={20} style={{ color: s.color }} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-base font-bold" style={{ color: 'var(--color-text)' }}>{s.label}</span>
                      <span className={`badge ${s.badge}`}>{result.status}</span>
                    </div>
                    <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                      Order: <span className="font-mono">{result.order_id}</span>
                    </div>
                  </div>
                </div>

                {/* Details grid */}
                <div className="space-y-3 mb-5">
                  {[
                    { label: 'AI Strategy', value: result.ai_strategy },
                    { label: 'Final Action', value: result.final_action_taken },
                    { label: 'Amount', value: `₹${((result.amount_paise || 0) / 100).toLocaleString('en-IN')}` },
                    result.guardrail_overridden && { label: 'Guardrail Override', value: result.override_reason },
                  ].filter(Boolean).map(({ label, value }) => (
                    <div key={label} className="rounded-lg px-3 py-2.5" style={{ background: 'var(--color-surface-2)' }}>
                      <div className="text-[10px] font-semibold uppercase tracking-wider mb-0.5" style={{ color: 'var(--color-text-muted)' }}>{label}</div>
                      <div className="text-xs" style={{ color: 'var(--color-text)' }}>{value}</div>
                    </div>
                  ))}
                </div>

                {/* Payment link */}
                {result.payment_link_url && (
                  <a
                    href={result.payment_link_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-primary w-full"
                  >
                    <ExternalLink size={14} />
                    Open Payment Link
                  </a>
                )}

                {/* Nudge */}
                {result.nudge_message_sent && (
                  <div
                    className="mt-3 rounded-lg px-3 py-2.5 text-xs italic"
                    style={{ background: 'var(--color-emerald-dim)', color: 'var(--color-emerald)', border: '1px solid rgba(16,185,129,0.2)' }}
                  >
                    "{result.nudge_message_sent}"
                  </div>
                )}
              </div>
            )
          })()}
        </div>
      </div>
    </div>
  )
}
