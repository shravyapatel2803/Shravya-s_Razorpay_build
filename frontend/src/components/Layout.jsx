import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Zap, Key, Settings, LogOut, Activity,
  TrendingUp, Shield
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { authAPI } from '../api/client'
import { toast } from 'sonner'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/webhook', icon: Zap, label: 'Webhook Tester' },
  { to: '/api-keys', icon: Key, label: 'API Keys' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

const roleBadge = {
  ADMIN: 'badge-indigo',
  ANALYST: 'badge-blue',
  VIEWER: 'badge-amber',
}

export default function Layout() {
  const { user, refreshToken, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = async () => {
    try { await authAPI.logout(refreshToken) } catch (_) {}
    logout()
    navigate('/')
    toast.success('Logged out successfully')
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--color-bg)' }}>
      {/* Sidebar */}
      <aside
        className="w-60 flex-shrink-0 flex flex-col border-r"
        style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}
      >
        {/* Logo */}
        <div className="px-5 py-5 border-b" style={{ borderColor: 'var(--color-border)' }}>
          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: 'var(--color-primary-glow)', border: '1px solid rgba(99,102,241,0.4)' }}
            >
              <Activity size={16} style={{ color: 'var(--color-primary-hover)' }} />
            </div>
            <div>
              <div className="text-sm font-bold" style={{ color: 'var(--color-text)' }}>
                Recovery<span className="gradient-text">AI</span>
              </div>
              <div className="text-[10px]" style={{ color: 'var(--color-text-muted)' }}>
                Razorpay Engine
              </div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User info */}
        <div className="px-3 pb-4 border-t pt-4" style={{ borderColor: 'var(--color-border)' }}>
          <div className="card p-3 mb-3" style={{ padding: '12px' }}>
            <div className="flex items-center gap-2 mb-2">
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
                style={{ background: 'var(--color-primary-glow)', color: 'var(--color-primary-hover)' }}
              >
                {user?.email?.[0]?.toUpperCase() ?? 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium truncate" style={{ color: 'var(--color-text)' }}>
                  {user?.business_name || user?.email?.split('@')[0]}
                </div>
                <div className="text-[10px] truncate" style={{ color: 'var(--color-text-muted)' }}>
                  {user?.email}
                </div>
              </div>
            </div>
            <span className={`badge ${roleBadge[user?.role] || 'badge-indigo'} text-[10px]`}>
              <Shield size={8} />
              {user?.role}
            </span>
          </div>
          <button className="nav-item w-full" onClick={handleLogout}>
            <LogOut size={15} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
