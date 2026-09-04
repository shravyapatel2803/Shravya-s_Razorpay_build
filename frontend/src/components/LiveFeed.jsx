import { useEffect, useRef, useState } from 'react'
import { gsap } from 'gsap'
import { CheckCircle, Clock, XCircle, ExternalLink, Cpu, X, ShieldCheck, MessageCircle } from 'lucide-react'

const statusConfig = {
  RECOVERED_PENDING_PAYMENT: {
    badge: 'badge-emerald',
    icon: CheckCircle,
    label: 'Recovered',
  },
  SCHEDULED_RETRY: {
    badge: 'badge-amber',
    icon: Clock,
    label: 'Retrying',
  },
  ABORTED: {
    badge: 'badge-red',
    icon: XCircle,
    label: 'Aborted',
  },
}

export function resolvePaymentLink(url, log) {
  if (!url) return null
  if (url.includes('mock_') || url.includes('rzp.io/i/mock')) {
    const slug = url.split('/').pop()?.split('?')[0] || 'mock_pay'
    const orderId = encodeURIComponent(log?.order_id || '')
    const amount = encodeURIComponent(log?.amount_inr || '')
    return `/pay/${slug}?order_id=${orderId}&amount=${amount}`
  }
  return url
}

// ---------------------------------------------------------------------------
// WhatsApp Preview Modal
// ---------------------------------------------------------------------------
function WhatsAppModal({ log, onClose }) {
  const overlayRef = useRef(null)
  const modalRef = useRef(null)
  const amountInr = log.amount_inr ? Number(log.amount_inr).toLocaleString('en-IN') : '0'

  // GSAP mount animation
  useEffect(() => {
    if (overlayRef.current && modalRef.current) {
      gsap.fromTo(overlayRef.current,
        { opacity: 0 },
        { opacity: 1, duration: 0.25, ease: 'power2.out' }
      )
      gsap.fromTo(modalRef.current,
        { scale: 0.88, opacity: 0, y: 24 },
        { scale: 1, opacity: 1, y: 0, duration: 0.35, ease: 'back.out(1.6)' }
      )
    }
  }, [])

  // Close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const timestamp = log.created_at
    ? new Date(log.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
    : '10:42'

  const nudgeText = log.nudge_message_sent ||
    'Aapka payment complete nahi ho saka. Kripya is link se retry karein. Dhanyavaad! 🙏'

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.72)', backdropFilter: 'blur(6px)' }}
      onClick={(e) => { if (e.target === overlayRef.current) onClose() }}
    >
      <div
        ref={modalRef}
        className="relative w-full max-w-sm"
        style={{ borderRadius: 20, overflow: 'hidden', boxShadow: '0 32px 64px rgba(0,0,0,0.5)' }}
      >
        {/* WhatsApp Header */}
        <div
          style={{
            background: 'linear-gradient(135deg, #075e54 0%, #128c7e 100%)',
            padding: '14px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          {/* Avatar */}
          <div
            style={{
              width: 42,
              height: 42,
              borderRadius: '50%',
              background: 'rgba(255,255,255,0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <ShieldCheck size={20} color="#fff" />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ color: '#fff', fontWeight: 700, fontSize: 15, letterSpacing: 0.1 }}>
                Razorpay Merchant
              </span>
              {/* Verified tick */}
              <span title="Verified Business">
                <ShieldCheck size={13} color="#25D366" />
              </span>
            </div>
            <div style={{ color: 'rgba(255,255,255,0.72)', fontSize: 11, marginTop: 1 }}>
              Official Business Account ✓
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255,255,255,0.12)',
              border: 'none',
              borderRadius: 8,
              padding: '4px 6px',
              cursor: 'pointer',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <X size={15} />
          </button>
        </div>

        {/* Chat Background */}
        <div
          style={{
            background: '#0d1117',
            padding: '16px 12px',
            minHeight: 260,
            backgroundImage:
              'radial-gradient(circle at 20% 80%, rgba(37,211,102,0.04) 0%, transparent 60%), ' +
              'radial-gradient(circle at 80% 20%, rgba(7,94,84,0.08) 0%, transparent 60%)',
          }}
        >
          {/* Order info chip */}
          <div
            style={{
              textAlign: 'center',
              marginBottom: 14,
            }}
          >
            <span
              style={{
                background: 'rgba(255,255,255,0.07)',
                color: 'rgba(255,255,255,0.45)',
                fontSize: 10,
                padding: '3px 10px',
                borderRadius: 20,
                letterSpacing: 0.5,
              }}
            >
              Order: {log.order_id}
            </span>
          </div>

          {/* Message Bubble */}
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div
              style={{
                background: '#1f2c34',
                borderRadius: '4px 16px 16px 16px',
                padding: '10px 14px',
                maxWidth: '86%',
                boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                border: '1px solid rgba(255,255,255,0.06)',
              }}
            >
              {/* Message icon row */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                <MessageCircle size={12} color="#25D366" />
                <span style={{ color: '#25D366', fontSize: 10, fontWeight: 600, letterSpacing: 0.5 }}>
                  PAYMENT RECOVERY
                </span>
              </div>

              {/* Hinglish copy */}
              <p
                style={{
                  color: '#e9edef',
                  fontSize: 13.5,
                  lineHeight: 1.55,
                  margin: '0 0 10px 0',
                  fontFamily: "'Inter', sans-serif",
                }}
              >
                {nudgeText}
              </p>

              {/* Amount highlight */}
              <div
                style={{
                  background: 'rgba(37,211,102,0.1)',
                  border: '1px solid rgba(37,211,102,0.2)',
                  borderRadius: 8,
                  padding: '6px 10px',
                  marginBottom: 10,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <span style={{ color: 'rgba(255,255,255,0.55)', fontSize: 11 }}>Amount due</span>
                <span style={{ color: '#25D366', fontWeight: 700, fontSize: 15 }}>
                  ₹{amountInr}
                </span>
              </div>

              {/* CTA Button */}
              {log.payment_link_url ? (
                <a
                  href={resolvePaymentLink(log.payment_link_url, log)}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6,
                    background: 'linear-gradient(135deg, #25D366 0%, #128c7e 100%)',
                    color: '#fff',
                    fontWeight: 700,
                    fontSize: 13,
                    padding: '9px 14px',
                    borderRadius: 10,
                    textDecoration: 'none',
                    boxShadow: '0 4px 12px rgba(37,211,102,0.35)',
                    transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-1px)'
                    e.currentTarget.style.boxShadow = '0 6px 18px rgba(37,211,102,0.45)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)'
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(37,211,102,0.35)'
                  }}
                >
                  <ExternalLink size={12} />
                  Pay ₹{amountInr} via UPI
                </a>
              ) : (
                <div
                  style={{
                    textAlign: 'center',
                    color: 'rgba(255,255,255,0.3)',
                    fontSize: 11,
                    padding: '6px 0',
                  }}
                >
                  Silent retry — no payment link dispatched
                </div>
              )}

              {/* Timestamp + Read receipts */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'flex-end',
                  alignItems: 'center',
                  gap: 4,
                  marginTop: 8,
                }}
              >
                <span style={{ color: 'rgba(255,255,255,0.35)', fontSize: 10 }}>{timestamp}</span>
                <span style={{ color: '#53bdeb', fontSize: 13, lineHeight: 1 }}>✓✓</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer note */}
        <div
          style={{
            background: '#0d1117',
            borderTop: '1px solid rgba(255,255,255,0.06)',
            padding: '10px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10 }}>
            This message was sent via Razorpay AI Recovery Engine · Meta Verified Business
          </span>
        </div>
      </div>
    </div>
  )
}


// ---------------------------------------------------------------------------
// Feed Item
// ---------------------------------------------------------------------------
function FeedItem({ log, idx }) {
  const ref = useRef(null)
  const [showModal, setShowModal] = useState(false)
  const cfg = statusConfig[log.status] || statusConfig.ABORTED
  const Icon = cfg.icon

  useEffect(() => {
    if (ref.current) {
      gsap.fromTo(ref.current,
        { x: 30, opacity: 0 },
        { x: 0, opacity: 1, duration: 0.4, ease: 'power2.out', delay: idx * 0.05 }
      )
    }
  }, [idx])

  const hasNudge = !!(log.nudge_message_sent || log.payment_link_url)

  return (
    <>
      <div
        ref={ref}
        className="flex items-start gap-3 py-3 border-b"
        style={{
          borderColor: 'var(--color-border)',
          cursor: hasNudge ? 'pointer' : 'default',
          borderRadius: 6,
          transition: 'background 0.15s ease',
        }}
        onClick={() => hasNudge && setShowModal(true)}
        onMouseEnter={(e) => {
          if (hasNudge) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent'
        }}
        title={hasNudge ? 'Click to preview WhatsApp message' : undefined}
      >
        {/* Status icon */}
        <div
          className="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center mt-0.5"
          style={{
            background:
              log.status === 'RECOVERED_PENDING_PAYMENT'
                ? 'rgba(16,185,129,0.15)'
                : log.status === 'SCHEDULED_RETRY'
                ? 'rgba(245,158,11,0.15)'
                : 'rgba(239,68,68,0.15)',
          }}
        >
          <Icon
            size={13}
            style={{
              color:
                log.status === 'RECOVERED_PENDING_PAYMENT'
                  ? 'var(--color-emerald)'
                  : log.status === 'SCHEDULED_RETRY'
                  ? 'var(--color-amber)'
                  : 'var(--color-red)',
            }}
          />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span
                className="text-xs font-semibold font-mono"
                style={{ color: 'var(--color-text)' }}
              >
                {log.order_id}
              </span>
              <span className={`badge ${cfg.badge}`}>{cfg.label}</span>
              {hasNudge && (
                <span title="WhatsApp nudge sent">
                  <MessageCircle size={10} style={{ color: '#25D366' }} />
                </span>
              )}
            </div>
            {log.amount_inr && (
              <span
                className="text-xs font-bold flex-shrink-0"
                style={{ color: 'var(--color-text)' }}
              >
                ₹{Number(log.amount_inr).toLocaleString('en-IN')}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 mt-1">
            <span className="text-[11px]" style={{ color: 'var(--color-text-muted)' }}>
              {log.error_code?.replace('BAD_REQUEST_PAYMENT_', '').replace('GATEWAY_ERROR_', '')}
            </span>
            <div className="flex items-center gap-1 text-[11px]" style={{ color: 'var(--color-text-muted)' }}>
              <Cpu size={9} />
              {log.ai_strategy?.replace('_', ' ')}
            </div>
          </div>

          {log.payment_link_url && (
            <a
              href={resolvePaymentLink(log.payment_link_url, log)}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[11px] mt-1"
              style={{ color: 'var(--color-primary-hover)' }}
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLink size={9} />
              Payment Link
            </a>
          )}
        </div>

        {/* Time */}
        <div className="text-[10px] flex-shrink-0" style={{ color: 'var(--color-text-muted)' }}>
          {log.created_at
            ? new Date(log.created_at).toLocaleTimeString('en-IN', {
                hour: '2-digit',
                minute: '2-digit',
              })
            : ''}
        </div>
      </div>

      {/* WhatsApp Modal */}
      {showModal && (
        <WhatsAppModal log={log} onClose={() => setShowModal(false)} />
      )}
    </>
  )
}

export default function LiveFeed({ logs }) {
  if (!logs?.length) {
    return (
      <div
        className="text-center py-10 text-sm"
        style={{ color: 'var(--color-text-muted)' }}
      >
        No recovery events yet. Fire a webhook to get started.
      </div>
    )
  }

  return (
    <div>
      {logs.map((log, idx) => (
        <FeedItem key={log.id} log={log} idx={idx} />
      ))}
    </div>
  )
}
