import { useEffect, useRef, useState } from 'react'
import { gsap } from 'gsap'
import { TrendingUp, TrendingDown, Minus, Info } from 'lucide-react'

export default function KpiCard({ label, value, prefix = '', suffix = '', color = 'indigo', icon: Icon, trend }) {
  const numRef = useRef(null)
  const cardRef = useRef(null)

  const colorMap = {
    indigo: { badge: 'badge-indigo', glow: 'var(--color-primary-glow)', icon: 'var(--color-primary-hover)' },
    emerald: { badge: 'badge-emerald', glow: 'rgba(16,185,129,0.15)', icon: 'var(--color-emerald)' },
    amber: { badge: 'badge-amber', glow: 'rgba(245,158,11,0.15)', icon: 'var(--color-amber)' },
    red: { badge: 'badge-red', glow: 'rgba(239,68,68,0.15)', icon: 'var(--color-red)' },
    blue: { badge: 'badge-blue', glow: 'rgba(59,130,246,0.15)', icon: 'var(--color-blue)' },
  }

  const c = colorMap[color] || colorMap.indigo

  useEffect(() => {
    if (numRef.current && typeof value === 'number') {
      const obj = { val: 0 }
      gsap.to(obj, {
        val: value,
        duration: 1.6,
        ease: 'power3.out',
        delay: 0.2,
        onUpdate: () => {
          if (numRef.current) {
            const v = Math.round(obj.val * 100) / 100
            numRef.current.textContent =
              prefix + (suffix === '%'
                ? v.toFixed(1)
                : v.toLocaleString('en-IN')) + suffix
          }
        },
      })
    }
  }, [value, prefix, suffix])

  return (
    <div
      ref={cardRef}
      className="card reveal-item relative overflow-hidden"
      style={{ cursor: 'default' }}
    >
      {/* Background glow */}
      <div
        className="absolute inset-0 opacity-30 pointer-events-none"
        style={{ background: `radial-gradient(ellipse at top left, ${c.glow}, transparent 70%)` }}
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-3 relative">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: c.glow, border: `1px solid ${c.icon}22` }}
        >
          {Icon && <Icon size={15} style={{ color: c.icon }} />}
        </div>
        {trend !== undefined && (
          <div className={`badge ${trend > 0 ? 'badge-emerald' : trend < 0 ? 'badge-red' : 'badge-amber'}`}>
            {trend > 0 ? <TrendingUp size={9} /> : trend < 0 ? <TrendingDown size={9} /> : <Minus size={9} />}
            {Math.abs(trend)}%
          </div>
        )}
      </div>

      {/* Value */}
      <div
        ref={numRef}
        className="text-2xl font-bold mb-1 relative"
        style={{ color: 'var(--color-text)', fontVariantNumeric: 'tabular-nums' }}
      >
        {prefix}0{suffix}
      </div>

      {/* Label */}
      <div className="text-xs font-medium relative" style={{ color: 'var(--color-text-muted)' }}>
        {label}
      </div>
    </div>
  )
}


// ---------------------------------------------------------------------------
// Net Merchant Value (Unit Economics) Card
// Formula: Net Value = Gross GMV - (Nudges × ₹0.80) - (Recovered GMV × 2% MDR)
// ---------------------------------------------------------------------------
const NUDGE_COST_INR = 0.80   // Meta WhatsApp Business API cost per message
const MDR_RATE = 0.02         // Razorpay processing fee (2%)

export function NetMarginCard({ grossRecoveredInr = 0, nudgesDispatched = 0 }) {
  const numRef = useRef(null)
  const cardRef = useRef(null)
  const [showTooltip, setShowTooltip] = useState(false)

  const messagingCost = nudgesDispatched * NUDGE_COST_INR
  const mdrCost = grossRecoveredInr * MDR_RATE
  const netValue = grossRecoveredInr - messagingCost - mdrCost
  const isPositive = netValue >= 0

  // ROI multiplier: net / cost (if cost > 0)
  const totalCost = messagingCost + mdrCost
  const roiX = totalCost > 0 ? (netValue / totalCost).toFixed(1) : '∞'

  useEffect(() => {
    if (numRef.current) {
      const obj = { val: 0 }
      gsap.to(obj, {
        val: netValue,
        duration: 1.8,
        ease: 'power3.out',
        delay: 0.3,
        onUpdate: () => {
          if (numRef.current) {
            const v = Math.round(obj.val * 100) / 100
            numRef.current.textContent = '₹' + v.toLocaleString('en-IN')
          }
        },
      })
    }
  }, [netValue])

  const glow = isPositive ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'
  const iconColor = isPositive ? 'var(--color-emerald)' : 'var(--color-red)'
  const textColor = isPositive ? 'var(--color-emerald)' : 'var(--color-red)'

  return (
    <div
      ref={cardRef}
      className="card reveal-item relative overflow-hidden"
      style={{ cursor: 'default' }}
    >
      {/* Glow */}
      <div
        className="absolute inset-0 opacity-30 pointer-events-none"
        style={{ background: `radial-gradient(ellipse at top left, ${glow}, transparent 70%)` }}
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-3 relative">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: glow, border: `1px solid ${iconColor}22` }}
        >
          {isPositive
            ? <TrendingUp size={15} style={{ color: iconColor }} />
            : <TrendingDown size={15} style={{ color: iconColor }} />
          }
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div
            className={`badge ${isPositive ? 'badge-emerald' : 'badge-red'}`}
            style={{ fontSize: 9 }}
          >
            {isPositive ? '📈' : '📉'} {roiX}x ROI
          </div>
          {/* Info icon with tooltip */}
          <div
            style={{ position: 'relative', cursor: 'pointer' }}
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
          >
            <Info size={13} style={{ color: 'var(--color-text-muted)' }} />
            {showTooltip && (
              <div
                style={{
                  position: 'absolute',
                  right: 0,
                  top: '100%',
                  marginTop: 6,
                  zIndex: 100,
                  background: '#1a1f2e',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 10,
                  padding: '10px 14px',
                  width: 220,
                  boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
                  fontSize: 11,
                  lineHeight: 1.7,
                  color: 'var(--color-text-muted)',
                  whiteSpace: 'nowrap',
                }}
              >
                <div style={{ color: 'var(--color-text)', fontWeight: 700, marginBottom: 6, fontSize: 12 }}>
                  Unit Economics Breakdown
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Gross Recovered GMV</span>
                  <span style={{ color: 'var(--color-emerald)' }}>+₹{grossRecoveredInr.toLocaleString('en-IN')}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Messaging cost ({nudgesDispatched} × ₹0.80)</span>
                  <span style={{ color: 'var(--color-red)' }}>−₹{messagingCost.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>MDR (2% Razorpay fee)</span>
                  <span style={{ color: 'var(--color-red)' }}>−₹{mdrCost.toFixed(2)}</span>
                </div>
                <div
                  style={{
                    borderTop: '1px solid rgba(255,255,255,0.08)',
                    marginTop: 6,
                    paddingTop: 6,
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontWeight: 700,
                    color: textColor,
                  }}
                >
                  <span>Net Merchant Value</span>
                  <span>₹{netValue.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Value */}
      <div
        ref={numRef}
        className="text-2xl font-bold mb-1 relative"
        style={{ color: textColor, fontVariantNumeric: 'tabular-nums' }}
      >
        ₹0
      </div>

      {/* Label */}
      <div className="text-xs font-medium relative" style={{ color: 'var(--color-text-muted)' }}>
        Net Merchant Value Recovered
        <div style={{ fontSize: 9, marginTop: 2, opacity: 0.65 }}>
          After messaging costs &amp; 2% MDR
        </div>
      </div>
    </div>
  )
}
