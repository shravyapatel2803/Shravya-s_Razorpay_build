import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { CheckCircle, Clock, XCircle, ExternalLink, Cpu } from 'lucide-react'

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

function FeedItem({ log, idx }) {
  const ref = useRef(null)
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

  return (
    <div
      ref={ref}
      className="flex items-start gap-3 py-3 border-b"
      style={{ borderColor: 'var(--color-border)' }}
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
            href={log.payment_link_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-[11px] mt-1"
            style={{ color: 'var(--color-primary-hover)' }}
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
