import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useAuthStore } from '../store/authStore'
import { authAPI } from '../api/client'
import { toast } from 'sonner'
import { Activity, Shield, Zap, TrendingUp, ArrowRight, Eye, EyeOff, Sparkles, UserCheck } from 'lucide-react'
import { useState } from 'react'

const FEATURES = [
  { icon: Zap, label: 'AI-Powered Recovery', desc: 'Gemini 3.5 Flash classifies failures & picks strategy' },
  { icon: Shield, label: 'Fintech Guardrails', desc: 'Deterministic compliance rules enforced on every decision' },
  { icon: TrendingUp, label: '95%+ GMV Recovery', desc: 'Autonomous payment links sent within milliseconds' },
]

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true)
  const [loading, setLoading] = useState(false)
  const [showPass, setShowPass] = useState(false)
  const navigate = useNavigate()
  const { setAuth, setUser, isAuthenticated } = useAuthStore()

  const heroRef = useRef(null)
  const formRef = useRef(null)
  const featuresRef = useRef(null)
  const canvasRef = useRef(null)

  const { register, handleSubmit, reset, setValue, formState: { errors } } = useForm()

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard')
  }, [isAuthenticated, navigate])

  // GSAP hero entrance
  useEffect(() => {
    const tl = gsap.timeline({ delay: 0.1 })
    tl.fromTo(heroRef.current,
      { opacity: 0, y: 30 },
      { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out' }
    )
    tl.fromTo('.feature-item',
      { opacity: 0, x: -20 },
      { opacity: 1, x: 0, duration: 0.5, stagger: 0.12, ease: 'power2.out' },
      '-=0.3'
    )
    tl.fromTo(formRef.current,
      { opacity: 0, y: 20 },
      { opacity: 1, y: 0, duration: 0.6, ease: 'power3.out' },
      '-=0.4'
    )
  }, [])

  // Animated particles
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let animId
    const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight }
    resize()
    window.addEventListener('resize', resize)

    const particles = Array.from({ length: 60 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.5 + 0.3,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      alpha: Math.random() * 0.4 + 0.1,
    }))

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      particles.forEach((p) => {
        p.x += p.vx; p.y += p.vy
        if (p.x < 0) p.x = canvas.width
        if (p.x > canvas.width) p.x = 0
        if (p.y < 0) p.y = canvas.height
        if (p.y > canvas.height) p.y = 0
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(99,102,241,${p.alpha})`
        ctx.fill()
      })
      animId = requestAnimationFrame(draw)
    }
    draw()
    return () => { cancelAnimationFrame(animId); window.removeEventListener('resize', resize) }
  }, [])

  // Toggle form with animation
  const toggleMode = () => {
    gsap.to(formRef.current, {
      opacity: 0, y: 10, duration: 0.2, ease: 'power2.in',
      onComplete: () => {
        setIsLogin(!isLogin)
        reset()
        gsap.fromTo(formRef.current,
          { opacity: 0, y: -10 },
          { opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' }
        )
      },
    })
  }

  const onSubmit = async (data) => {
    setLoading(true)
    try {
      if (isLogin) {
        const res = await authAPI.login({ email: data.email, password: data.password })
        const { access_token, refresh_token } = res.data
        setAuth({ access_token, refresh_token, user: null })
        const meRes = await authAPI.me()
        setUser(meRes.data)
        toast.success(`Welcome back, ${meRes.data.business_name || meRes.data.email}!`)
        navigate('/dashboard')
      } else {
        await authAPI.register({
          email: data.email,
          password: data.password,
          business_name: data.business_name,
          razorpay_key_id: data.razorpay_key_id || undefined,
          razorpay_key_secret: data.razorpay_key_secret || undefined,
          gemini_api_key: data.gemini_api_key || undefined,
        })
        toast.success('Account created! Please sign in.')
        toggleMode()
      }
    } catch (err) {
      const msg = err.response?.data?.detail
      toast.error(typeof msg === 'string' ? msg : 'Authentication failed. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  const handleDemoLogin = async () => {
    setValue('email', 'demo@razorpay-recovery.dev')
    setValue('password', 'DemoPass@2026!')
    setIsLogin(true)
    setLoading(true)
    try {
      const res = await authAPI.login({
        email: 'demo@razorpay-recovery.dev',
        password: 'DemoPass@2026!',
      })
      const { access_token, refresh_token } = res.data
      setAuth({ access_token, refresh_token, user: null })
      const meRes = await authAPI.me()
      setUser(meRes.data)
      toast.success(`Signed in as Demo Merchant!`)
      navigate('/dashboard')
    } catch (err) {
      toast.error('Could not auto-login to demo account. Please try manual sign in.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--color-bg)' }}>
      {/* Particles */}
      <canvas ref={canvasRef} className="fixed inset-0 pointer-events-none" style={{ zIndex: 0 }} />

      {/* Left — Hero */}
      <div className="hidden lg:flex flex-col justify-center flex-1 px-16 relative z-10">
        <div ref={heroRef}>
          {/* Badge */}
          <div className="badge badge-indigo mb-6 w-fit">
            <Activity size={10} />
            Razorpay AI Buildathon 2026
          </div>

          <h1 className="text-5xl font-black leading-tight mb-4" style={{ color: 'var(--color-text)' }}>
            Autonomous<br />
            <span className="gradient-text">Revenue Recovery</span><br />
            Engine
          </h1>

          <p className="text-base mb-10" style={{ color: 'var(--color-text-muted)', maxWidth: 420 }}>
            When payments fail, our AI doesn't sleep.{' '}
            Every rupee is analysed, guardrailed, and recovered — automatically.
          </p>

          {/* Features */}
          <div ref={featuresRef} className="space-y-4">
            {FEATURES.map(({ icon: Icon, label, desc }) => (
              <div key={label} className="feature-item flex items-start gap-3">
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: 'var(--color-primary-glow)', border: '1px solid rgba(99,102,241,0.3)' }}
                >
                  <Icon size={16} style={{ color: 'var(--color-primary-hover)' }} />
                </div>
                <div>
                  <div className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>{label}</div>
                  <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right — Auth Form */}
      <div className="flex-1 lg:max-w-md flex items-center justify-center px-6 py-12 relative z-10">
        <div ref={formRef} className="w-full max-w-sm">
          {/* Card */}
          <div className="card animated-border" style={{ padding: 28 }}>
            <div className="mb-6">
              <h2 className="text-xl font-bold mb-1" style={{ color: 'var(--color-text)' }}>
                {isLogin ? 'Sign in' : 'Create account'}
              </h2>
              <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                {isLogin
                  ? 'Access your recovery dashboard'
                  : 'Start recovering failed payments with AI'}
              </p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {!isLogin && (
                <div>
                  <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>
                    Business Name
                  </label>
                  <input
                    className="input"
                    placeholder="Acme Store Pvt. Ltd."
                    {...register('business_name', { required: !isLogin })}
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>
                  Email Address
                </label>
                <input
                  className="input"
                  type="email"
                  placeholder="you@business.com"
                  {...register('email', { required: true })}
                />
              </div>

              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>
                  Password
                </label>
                <div className="relative">
                  <input
                    className="input pr-10"
                    type={showPass ? 'text' : 'password'}
                    placeholder={isLogin ? '••••••••' : 'Min. 8 characters'}
                    {...register('password', { required: true, minLength: 8 })}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    className="absolute right-3 top-1/2 -translate-y-1/2"
                    style={{ color: 'var(--color-text-muted)' }}
                  >
                    {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              {!isLogin && (
                <>
                  <div className="border-t pt-4" style={{ borderColor: 'var(--color-border)' }}>
                    <div className="text-xs font-medium mb-3" style={{ color: 'var(--color-text-muted)' }}>
                      API Credentials <span style={{ color: 'var(--color-text-subtle)' }}>(optional — can add later)</span>
                    </div>
                    <div className="space-y-3">
                      <input
                        className="input"
                        placeholder="Razorpay Key ID (rzp_test_...)"
                        {...register('razorpay_key_id')}
                      />
                      <input
                        className="input"
                        type="password"
                        placeholder="Razorpay Key Secret"
                        {...register('razorpay_key_secret')}
                      />
                      <input
                        className="input"
                        type="password"
                        placeholder="Gemini API Key"
                        {...register('gemini_api_key')}
                      />
                    </div>
                  </div>
                </>
              )}

              <button
                type="submit"
                className="btn btn-primary w-full mt-2"
                disabled={loading}
              >
                {loading ? (
                  <div className="spinner" />
                ) : (
                  <>
                    {isLogin ? 'Sign In' : 'Create Account'}
                    <ArrowRight size={15} />
                  </>
                )}
              </button>
            </form>

            <div className="text-center mt-4 text-xs" style={{ color: 'var(--color-text-muted)' }}>
              {isLogin ? "Don't have an account?" : 'Already have an account?'}{' '}
              <button
                onClick={toggleMode}
                className="font-semibold"
                style={{ color: 'var(--color-primary-hover)' }}
              >
                {isLogin ? 'Create one' : 'Sign in'}
              </button>
            </div>

            {/* Quick Demo Account Card */}
            <div
              className="mt-6 pt-5 border-t"
              style={{ borderColor: 'var(--color-border)' }}
            >
              <div
                className="rounded-xl p-3.5"
                style={{
                  background: 'rgba(99,102,241,0.07)',
                  border: '1px solid rgba(99,102,241,0.25)',
                }}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <Sparkles size={13} style={{ color: 'var(--color-primary-hover)' }} />
                    <span className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>
                      Quick Demo Access
                    </span>
                  </div>
                  <span className="badge badge-indigo text-[10px]">Ready</span>
                </div>
                <div className="text-[11px] mb-3" style={{ color: 'var(--color-text-muted)' }}>
                  Auto-load pre-configured Admin credentials with Razorpay test keys and Gemini AI setup:
                </div>
                <div
                  className="rounded px-2.5 py-1.5 font-mono text-[10px] mb-3 space-y-0.5"
                  style={{ background: 'var(--color-surface-2)', color: 'var(--color-text-muted)' }}
                >
                  <div><span style={{ color: 'var(--color-primary-hover)' }}>Email:</span> demo@razorpay-recovery.dev</div>
                  <div><span style={{ color: 'var(--color-primary-hover)' }}>Pass:</span> DemoPass@2026!</div>
                </div>
                <button
                  type="button"
                  onClick={handleDemoLogin}
                  disabled={loading}
                  className="btn btn-outline btn-sm w-full font-medium"
                  style={{ borderColor: 'rgba(99,102,241,0.4)', color: 'var(--color-primary-hover)' }}
                >
                  <UserCheck size={13} />
                  1-Click Demo Login
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
