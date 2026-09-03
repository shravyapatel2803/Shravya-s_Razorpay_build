import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, ReferenceLine
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="card" style={{ padding: '10px 14px', minWidth: 160 }}>
        <div className="text-xs font-semibold mb-2" style={{ color: 'var(--color-text-muted)' }}>
          {label}
        </div>
        {payload.map((entry) => (
          <div key={entry.name} className="flex items-center justify-between gap-4">
            <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{entry.name}</div>
            <div className="text-sm font-bold" style={{ color: entry.color }}>
              ₹{Number(entry.value).toLocaleString('en-IN')}
            </div>
          </div>
        ))}
      </div>
    )
  }
  return null
}

export default function RecoveryFunnel({ data }) {
  if (!data) return null

  const chartData = [
    { name: 'At Risk', value: data.total_gmv_at_risk_inr ?? 0, color: '#6366f1' },
    { name: 'Recovering', value: data.total_gmv_recovered_inr ?? 0, color: '#10b981' },
    { name: 'Retrying', value: data.total_gmv_scheduled_inr ?? 0, color: '#f59e0b' },
    { name: 'Aborted', value: data.total_gmv_aborted_inr ?? 0, color: '#ef4444' },
  ]

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barCategoryGap="30%">
        <CartesianGrid
          strokeDasharray="3 3"
          vertical={false}
          stroke="var(--color-border)"
        />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)', fontFamily: 'Inter' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: 'var(--color-text-muted)', fontFamily: 'Inter' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <Bar dataKey="value" name="GMV" radius={[5, 5, 0, 0]}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.color} fillOpacity={0.85} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
