import { useEffect, useRef, useState, useCallback } from 'react'
import { gsap } from 'gsap'
import {
  TrendingUp, IndianRupee, RefreshCw, AlertTriangle,
  Activity, RotateCcw, ChevronRight
} from 'lucide-react'
import { toast } from 'sonner'
import KpiCard, { NetMarginCard } from '../components/KpiCard'
import RecoveryFunnel from '../components/RecoveryFunnel'
import LiveFeed from '../components/LiveFeed'
import { recoveryAPI } from '../api/client'

export default function DashboardPage() {
  const [metrics, setMetrics] = useState(null)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState(false)
  const kpiRef = useRef(null)

  const fetchData = useCallback(async () => {
    try {
      const [mRes, lRes] = await Promise.all([
        recoveryAPI.metrics(),
        recoveryAPI.logs(20),
      ])
      setMetrics(mRes.data)
      setLogs(lRes.data)
    } catch {
      toast.error('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 15000) // auto-refresh every 15s
    return () => clearInterval(interval)
  }, [fetchData])

  // GSAP stagger on KPI cards
  useEffect(() => {
    if (!loading && kpiRef.current) {
      gsap.to('.reveal-item', {
        opacity: 1,
        y: 0,
        duration: 0.6,
        stagger: 0.1,
        ease: 'power3.out',
        delay: 0.1,
      })
    }
  }, [loading])

  const handleReset = async () => {
    if (!window.confirm('Reset the audit ledger? All recovery history will be cleared.')) return
    setResetting(true)
    try {
      await recoveryAPI.reset()
      toast.success('Audit ledger reset.')
      await fetchData()
    } catch {
      toast.error('Failed to reset ledger.')
    } finally {
      setResetting(false)
    }
  }

  const kpis = metrics
    ? [
        {
          label: 'Total GMV At Risk',
          value: metrics.total_gmv_at_risk_inr,
          prefix: '₹',
          color: 'indigo',
          icon: IndianRupee,
        },
        {
          label: 'GMV Under Recovery',
          value: metrics.total_gmv_recovered_inr,
          prefix: '₹',
          color: 'emerald',
          icon: TrendingUp,
        },
        {
          label: 'Queued for Retry',
          value: metrics.total_gmv_scheduled_inr,
          prefix: '₹',
          color: 'amber',
          icon: RefreshCw,
        },
        {
          label: 'Net Recovery Rate',
          value: metrics.recovery_success_rate_pct,
          suffix: '%',
          color: metrics.recovery_success_rate_pct >= 80 ? 'emerald' : 'amber',
          icon: Activity,
        },
      ]
    : []

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-7">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
            Recovery Dashboard
          </h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
            Real-time AI payment recovery metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--color-text-muted)' }}>
            <div className="pulse-dot" />
            Live
          </div>
          <button
            onClick={fetchData}
            className="btn btn-outline btn-sm"
            title="Refresh"
          >
            <RefreshCw size={13} />
            Refresh
          </button>
          <button
            onClick={handleReset}
            className="btn btn-danger btn-sm"
            disabled={resetting}
          >
            {resetting ? <div className="spinner" /> : <RotateCcw size={13} />}
            Reset
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card h-28 animate-pulse" style={{ background: 'var(--color-surface-2)' }} />
          ))}
        </div>
      ) : (
        <div ref={kpiRef} className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          {kpis.map((kpi) => (
            <KpiCard key={kpi.label} {...kpi} />
          ))}
          {metrics && (
            <NetMarginCard
              grossRecoveredInr={metrics.total_gmv_recovered_inr ?? 0}
              nudgesDispatched={metrics.nudge_dispatched_count ?? 0}
            />
          )}
        </div>
      )}

      {/* Two-column: Chart + Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Funnel Chart */}
        <div className="lg:col-span-2 card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                GMV Recovery Funnel
              </div>
              <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Distribution by recovery stage
              </div>
            </div>
          </div>
          {loading ? (
            <div className="h-52 flex items-center justify-center" style={{ color: 'var(--color-text-muted)' }}>
              <div className="spinner" />
            </div>
          ) : (
            <RecoveryFunnel data={metrics} />
          )}

          {/* Stats below chart */}
          {metrics && (
            <div
              className="mt-4 pt-4 border-t grid grid-cols-2 gap-2 text-center"
              style={{ borderColor: 'var(--color-border)' }}
            >
              <div>
                <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Events</div>
                <div className="text-lg font-bold" style={{ color: 'var(--color-text)' }}>
                  {metrics.total_events_processed}
                </div>
              </div>
              <div>
                <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Guardrails Fired</div>
                <div className="text-lg font-bold" style={{ color: 'var(--color-amber)' }}>
                  {metrics.guardrail_overrides ?? 0}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Live Feed */}
        <div className="lg:col-span-3 card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                Recovery Events
              </div>
              <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Last 20 decisions
              </div>
            </div>
            <a
              href="/webhook"
              className="btn btn-outline btn-sm"
              style={{ textDecoration: 'none' }}
            >
              Test Webhook
              <ChevronRight size={12} />
            </a>
          </div>
          <div className="overflow-y-auto" style={{ maxHeight: 380 }}>
            {loading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-14 rounded-lg animate-pulse" style={{ background: 'var(--color-surface-2)' }} />
                ))}
              </div>
            ) : (
              <LiveFeed logs={logs} />
            )}
          </div>
        </div>
      </div>

      {/* Guardrail alert */}
      {metrics?.guardrail_overrides > 0 && (
        <div
          className="mt-4 flex items-center gap-3 rounded-xl px-4 py-3"
          style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)' }}
        >
          <AlertTriangle size={14} style={{ color: 'var(--color-amber)' }} />
          <span className="text-xs" style={{ color: 'var(--color-amber)' }}>
            <strong>{metrics.guardrail_overrides}</strong> guardrail override(s) applied — compliance rules auto-corrected the AI strategy.
          </span>
        </div>
      )}
    </div>
  )
}
