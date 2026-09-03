import { useEffect, useRef, useState } from 'react'
import { gsap } from 'gsap'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { Save, Key, User, Shield, Plus, Trash2, Check } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { authAPI } from '../api/client'

function Section({ title, children }) {
  return (
    <div className="card reveal-item mb-4">
      <div
        className="text-xs font-semibold uppercase tracking-widest mb-4"
        style={{ color: 'var(--color-text-muted)' }}
      >
        {title}
      </div>
      {children}
    </div>
  )
}

export default function SettingsPage() {
  const { user, setUser } = useAuthStore()
  const [subUsers, setSubUsers] = useState([])
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingPwd, setSavingPwd] = useState(false)
  const [creatingUser, setCreatingUser] = useState(false)
  const pageRef = useRef(null)

  const profileForm = useForm({ defaultValues: {
    business_name: user?.business_name || '',
    razorpay_key_id: user?.razorpay_key_id || '',
    razorpay_key_secret: '',
    gemini_api_key: '',
    auto_recovery_enabled: user?.auto_recovery_enabled ?? true,
  }})

  const pwdForm = useForm()
  const subUserForm = useForm({ defaultValues: { role: 'ANALYST' }})

  // GSAP page entrance
  useEffect(() => {
    gsap.to('.reveal-item', {
      opacity: 1, y: 0, duration: 0.5, stagger: 0.08, ease: 'power3.out', delay: 0.1
    })
  }, [])

  // Load sub-users if ADMIN
  useEffect(() => {
    if (user?.role === 'ADMIN') {
      authAPI.listSubUsers().then(r => setSubUsers(r.data)).catch(() => {})
    }
  }, [user])

  const onSaveProfile = async (data) => {
    setSavingProfile(true)
    try {
      const payload = {}
      if (data.business_name) payload.business_name = data.business_name
      if (data.razorpay_key_id) payload.razorpay_key_id = data.razorpay_key_id
      if (data.razorpay_key_secret) payload.razorpay_key_secret = data.razorpay_key_secret
      if (data.gemini_api_key) payload.gemini_api_key = data.gemini_api_key
      payload.auto_recovery_enabled = data.auto_recovery_enabled

      const res = await authAPI.updateMe(payload)
      setUser(res.data)
      toast.success('Profile updated.')
    } catch {
      toast.error('Failed to update profile.')
    } finally { setSavingProfile(false) }
  }

  const onChangePassword = async (data) => {
    if (data.new_password !== data.confirm_password) {
      toast.error('New passwords do not match.')
      return
    }
    setSavingPwd(true)
    try {
      await authAPI.changePassword({
        current_password: data.current_password,
        new_password: data.new_password,
      })
      toast.success('Password changed. You will be logged out.')
      pwdForm.reset()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to change password.')
    } finally { setSavingPwd(false) }
  }

  const onCreateSubUser = async (data) => {
    setCreatingUser(true)
    try {
      const res = await authAPI.createSubUser(data)
      setSubUsers(prev => [...prev, res.data])
      subUserForm.reset({ role: 'ANALYST' })
      toast.success(`Sub-user ${data.email} created.`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create sub-user.')
    } finally { setCreatingUser(false) }
  }

  const onDeactivate = async (id, email) => {
    if (!window.confirm(`Deactivate ${email}?`)) return
    try {
      await authAPI.deactivateSubUser(id)
      setSubUsers(prev => prev.map(u => u.id === id ? { ...u, is_active: false } : u))
      toast.success(`${email} deactivated.`)
    } catch { toast.error('Failed to deactivate user.') }
  }

  return (
    <div ref={pageRef} className="p-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-7">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>Settings</h1>
        <p className="text-sm mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
          Manage your profile, credentials, and team access
        </p>
      </div>

      {/* Profile */}
      <Section title="Profile & Credentials">
        <form onSubmit={profileForm.handleSubmit(onSaveProfile)} className="space-y-4">
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>Business Name</label>
            <input className="input" {...profileForm.register('business_name')} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>Email</label>
              <input className="input" value={user?.email || ''} disabled style={{ opacity: 0.5 }} />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>Role</label>
              <div className="input flex items-center gap-2" style={{ opacity: 0.5, cursor: 'default' }}>
                <Shield size={13} />
                {user?.role}
              </div>
            </div>
          </div>
          <div className="border-t pt-4" style={{ borderColor: 'var(--color-border)' }}>
            <div className="text-xs font-semibold mb-3" style={{ color: 'var(--color-text-muted)' }}>API Credentials</div>
            <div className="space-y-3">
              <input className="input" placeholder="Razorpay Key ID" {...profileForm.register('razorpay_key_id')} />
              <input className="input" type="password" placeholder="Razorpay Key Secret (leave blank to keep)" {...profileForm.register('razorpay_key_secret')} />
              <input className="input" type="password" placeholder="Gemini API Key (leave blank to keep)" {...profileForm.register('gemini_api_key')} />
            </div>
          </div>
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" {...profileForm.register('auto_recovery_enabled')} className="w-4 h-4 rounded" />
              <span className="text-xs" style={{ color: 'var(--color-text)' }}>Auto-recovery enabled</span>
            </label>
            <button type="submit" className="btn btn-primary btn-sm" disabled={savingProfile}>
              {savingProfile ? <div className="spinner" /> : <><Save size={13} /> Save Changes</>}
            </button>
          </div>
        </form>
      </Section>

      {/* Password */}
      <Section title="Change Password">
        <form onSubmit={pwdForm.handleSubmit(onChangePassword)} className="space-y-3">
          <input className="input" type="password" placeholder="Current password" {...pwdForm.register('current_password', { required: true })} />
          <input className="input" type="password" placeholder="New password (min. 8 characters)" {...pwdForm.register('new_password', { required: true, minLength: 8 })} />
          <input className="input" type="password" placeholder="Confirm new password" {...pwdForm.register('confirm_password', { required: true })} />
          <button type="submit" className="btn btn-outline btn-sm" disabled={savingPwd}>
            {savingPwd ? <div className="spinner" /> : <><Key size={13} /> Update Password</>}
          </button>
        </form>
      </Section>

      {/* Sub-users (ADMIN only) */}
      {user?.role === 'ADMIN' && (
        <Section title="Team Members">
          {/* Create sub-user */}
          <form onSubmit={subUserForm.handleSubmit(onCreateSubUser)} className="flex gap-2 mb-5">
            <input
              className="input flex-1"
              placeholder="team@company.com"
              type="email"
              {...subUserForm.register('email', { required: true })}
            />
            <input
              className="input w-36"
              type="password"
              placeholder="Password"
              {...subUserForm.register('password', { required: true, minLength: 8 })}
            />
            <select className="input w-32" {...subUserForm.register('role')}>
              <option value="ANALYST">Analyst</option>
              <option value="VIEWER">Viewer</option>
            </select>
            <button type="submit" className="btn btn-primary flex-shrink-0" disabled={creatingUser}>
              {creatingUser ? <div className="spinner" /> : <><Plus size={14} /> Invite</>}
            </button>
          </form>

          {/* Sub-user list */}
          {subUsers.length === 0 ? (
            <div className="text-center py-8 text-sm" style={{ color: 'var(--color-text-muted)' }}>
              No team members yet.
            </div>
          ) : (
            <div className="space-y-2">
              {subUsers.map((u) => (
                <div
                  key={u.id}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg"
                  style={{ background: 'var(--color-surface-2)' }}
                >
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                    style={{ background: 'var(--color-primary-glow)', color: 'var(--color-primary-hover)' }}
                  >
                    {u.email[0].toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate" style={{ color: 'var(--color-text)' }}>{u.email}</div>
                    <span className={`badge badge-${u.role === 'ANALYST' ? 'blue' : 'amber'} text-[10px]`}>
                      {u.role}
                    </span>
                  </div>
                  {u.is_active ? (
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => onDeactivate(u.id, u.email)}
                    >
                      <Trash2 size={11} />
                    </button>
                  ) : (
                    <span className="badge badge-red text-[10px]">Deactivated</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}
    </div>
  )
}
