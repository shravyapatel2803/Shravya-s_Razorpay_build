import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

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
