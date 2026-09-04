import { useState, useEffect, useRef } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { gsap } from 'gsap'
import {
  Shield,
  Lock,
  CheckCircle,
  QrCode,
  CreditCard,
  Building2,
  Smartphone,
  ArrowLeft,
  Sparkles,
  ExternalLink,
  Copy,
  Check,
  Zap,
} from 'lucide-react'

export default function CheckoutPage() {
  const { linkId } = useParams()
  const [searchParams] = useSearchParams()

  const orderId = searchParams.get('order_id') || linkId?.replace('mock_', 'order_') || 'order_RECOVERY_DEMO'
  const amount = searchParams.get('amount') || '2,500'
  const formattedAmount = Number(amount.replace(/,/g, '')).toLocaleString('en-IN')

  const [activeTab, setActiveTab] = useState('upi') // 'upi' | 'card' | 'netbanking'
  const [paymentState, setPaymentState] = useState('idle') // 'idle' | 'processing' | 'success'
  const [copiedVpa, setCopiedVpa] = useState(false)
  const [upiId, setUpiId] = useState('customer@okhdfcbank')
  const [cardNumber, setCardNumber] = useState('4111 2222 3333 4444')
  const [expiry, setExpiry] = useState('12/28')
  const [cvv, setCvv] = useState('123')
  const [selectedBank, setSelectedBank] = useState('HDFC')

  const cardRef = useRef(null)
  const successRef = useRef(null)

  // GSAP entrance animation
  useEffect(() => {
    if (cardRef.current) {
      gsap.fromTo(
        cardRef.current,
        { opacity: 0, y: 30, scale: 0.96 },
        { opacity: 1, y: 0, scale: 1, duration: 0.6, ease: 'power3.out' }
      )
    }
  }, [])

  const handlePay = () => {
    setPaymentState('processing')
    setTimeout(() => {
      setPaymentState('success')
      if (successRef.current) {
        gsap.fromTo(
          successRef.current,
          { scale: 0.8, opacity: 0 },
          { scale: 1, opacity: 1, duration: 0.5, ease: 'back.out(1.7)' }
        )
      }
    }, 1500)
  }

  const copyVpa = () => {
    navigator.clipboard.writeText('razorpay.recovery@icici')
    setCopiedVpa(true)
    setTimeout(() => setCopiedVpa(false), 2000)
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'radial-gradient(ellipse at 50% 20%, #0d1a2d 0%, #060b13 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 16px',
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        color: '#e2e8f0',
      }}
    >
      {/* Top Test Sandbox Banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          background: 'rgba(51, 149, 255, 0.12)',
          border: '1px solid rgba(51, 149, 255, 0.3)',
          borderRadius: 24,
          padding: '6px 14px',
          fontSize: 12,
          color: '#3395ff',
          marginBottom: 20,
          fontWeight: 500,
        }}
      >
        <Zap size={14} />
        <span>Razorpay Autonomous Recovery Sandbox • Simulation Mode</span>
      </div>

      {/* Main Checkout Card */}
      <div
        ref={cardRef}
        style={{
          width: '100%',
          maxWidth: 460,
          background: '#111827',
          borderRadius: 20,
          boxShadow: '0 24px 56px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.08)',
          overflow: 'hidden',
        }}
      >
        {/* Razorpay Brand Header */}
        <div
          style={{
            background: 'linear-gradient(135deg, #0c2340 0%, #07192f 100%)',
            borderBottom: '1px solid rgba(51, 149, 255, 0.2)',
            padding: '18px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Razorpay lightning glyph */}
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: 'linear-gradient(135deg, #3395ff 0%, #0052cc 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 4px 12px rgba(51,149,255,0.4)',
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path
                  d="M13.5 2L3 13.5H10.5L9 22L21 9H13.5L15 2H13.5Z"
                  fill="#ffffff"
                  stroke="#ffffff"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 16, color: '#ffffff', letterSpacing: 0.2 }}>
                Razorpay <span style={{ color: '#3395ff', fontWeight: 500, fontSize: 12 }}>RECOVERY</span>
              </div>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', marginTop: 1 }}>
                Merchant: Acme Store (Verified)
              </div>
            </div>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              fontSize: 11,
              color: 'rgba(255,255,255,0.6)',
              background: 'rgba(255,255,255,0.06)',
              padding: '4px 8px',
              borderRadius: 6,
            }}
          >
            <Lock size={11} color="#22c55e" />
            <span>256-bit SSL</span>
          </div>
        </div>

        {/* Payment Summary / Amount Section */}
        <div
          style={{
            padding: '16px 20px',
            background: 'rgba(255,255,255,0.02)',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              Amount Due
            </div>
            <div style={{ fontSize: 26, fontWeight: 800, color: '#3395ff', marginTop: 2 }}>
              ₹{formattedAmount}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>Order Reference</div>
            <div
              style={{
                fontSize: 12,
                fontFamily: 'monospace',
                color: 'rgba(255,255,255,0.8)',
                background: 'rgba(255,255,255,0.05)',
                padding: '3px 8px',
                borderRadius: 6,
                marginTop: 3,
              }}
            >
              {orderId}
            </div>
          </div>
        </div>

        {paymentState === 'success' ? (
          /* SUCCESS STATE */
          <div
            ref={successRef}
            style={{
              padding: '36px 24px',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: '50%',
                background: 'rgba(34, 197, 94, 0.15)',
                border: '2px solid #22c55e',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: 16,
                boxShadow: '0 0 24px rgba(34, 197, 94, 0.3)',
              }}
            >
              <CheckCircle size={36} color="#22c55e" />
            </div>

            <h3 style={{ fontSize: 20, fontWeight: 700, color: '#ffffff', margin: '0 0 6px 0' }}>
              Payment Successful!
            </h3>
            <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.6)', margin: '0 0 20px 0', maxWidth: 320 }}>
              Your payment of <strong style={{ color: '#22c55e' }}>₹{formattedAmount}</strong> has been received by Acme Store. The recovery cycle is complete.
            </p>

            <div
              style={{
                width: '100%',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: 12,
                padding: '12px 16px',
                marginBottom: 24,
                fontSize: 12,
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
                textAlign: 'left',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'rgba(255,255,255,0.4)' }}>Payment ID:</span>
                <span style={{ fontFamily: 'monospace', color: '#3395ff' }}>
                  pay_{Math.random().toString(36).substring(2, 10)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'rgba(255,255,255,0.4)' }}>Status:</span>
                <span style={{ color: '#22c55e', fontWeight: 600 }}>CAPTURED</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'rgba(255,255,255,0.4)' }}>Method:</span>
                <span style={{ textTransform: 'uppercase' }}>{activeTab}</span>
              </div>
            </div>

            <Link
              to="/dashboard"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                background: 'linear-gradient(135deg, #3395ff 0%, #0052cc 100%)',
                color: '#ffffff',
                padding: '10px 24px',
                borderRadius: 10,
                textDecoration: 'none',
                fontWeight: 600,
                fontSize: 13,
                boxShadow: '0 4px 14px rgba(51,149,255,0.3)',
              }}
            >
              <ArrowLeft size={14} /> Back to Recovery Engine Dashboard
            </Link>
          </div>
        ) : (
          /* PAYMENT FORM */
          <div style={{ padding: '20px' }}>
            {/* Payment Method Tabs */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 8,
                marginBottom: 20,
              }}
            >
              {[
                { id: 'upi', label: 'UPI / QR', icon: QrCode },
                { id: 'card', label: 'Cards', icon: CreditCard },
                { id: 'netbanking', label: 'NetBanking', icon: Building2 },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 6,
                    padding: '10px 8px',
                    borderRadius: 10,
                    border:
                      activeTab === id
                        ? '1px solid #3395ff'
                        : '1px solid rgba(255,255,255,0.08)',
                    background:
                      activeTab === id
                        ? 'rgba(51, 149, 255, 0.12)'
                        : 'rgba(255,255,255,0.03)',
                    color: activeTab === id ? '#3395ff' : 'rgba(255,255,255,0.6)',
                    cursor: 'pointer',
                    fontSize: 12,
                    fontWeight: activeTab === id ? 600 : 400,
                    transition: 'all 0.15s ease',
                  }}
                >
                  <Icon size={16} />
                  <span>{label}</span>
                </button>
              ))}
            </div>

            {/* TAB: UPI */}
            {activeTab === 'upi' && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                {/* Simulated QR Code */}
                <div
                  style={{
                    background: '#ffffff',
                    padding: 14,
                    borderRadius: 14,
                    boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                    marginBottom: 14,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                  }}
                >
                  <div
                    style={{
                      width: 140,
                      height: 140,
                      background: 'radial-gradient(circle, #000 40%, transparent 40%) 0 0/10px 10px, radial-gradient(circle, #000 40%, transparent 40%) 5px 5px/10px 10px #fff',
                      borderRadius: 8,
                      border: '2px solid #000',
                      position: 'relative',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <div
                      style={{
                        background: '#0c2340',
                        color: '#3395ff',
                        padding: '4px 6px',
                        borderRadius: 4,
                        fontSize: 10,
                        fontWeight: 800,
                      }}
                    >
                      UPI
                    </div>
                  </div>
                  <span style={{ color: '#475569', fontSize: 11, fontWeight: 600, marginTop: 8 }}>
                    Scan with any UPI App
                  </span>
                </div>

                {/* UPI Apps Row */}
                <div
                  style={{
                    display: 'flex',
                    gap: 8,
                    marginBottom: 14,
                    fontSize: 11,
                    color: 'rgba(255,255,255,0.5)',
                  }}
                >
                  {['Google Pay', 'PhonePe', 'Paytm', 'BHIM', 'CRED'].map((app) => (
                    <span
                      key={app}
                      style={{
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.08)',
                        padding: '3px 7px',
                        borderRadius: 6,
                        fontSize: 10,
                      }}
                    >
                      {app}
                    </span>
                  ))}
                </div>

                {/* VPA Input */}
                <div style={{ width: '100%', marginBottom: 14 }}>
                  <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', display: 'block', marginBottom: 4 }}>
                    Or enter UPI ID
                  </label>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <input
                      type="text"
                      value={upiId}
                      onChange={(e) => setUpiId(e.target.value)}
                      style={{
                        flex: 1,
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.12)',
                        borderRadius: 8,
                        padding: '8px 12px',
                        color: '#fff',
                        fontSize: 13,
                        outline: 'none',
                      }}
                      placeholder="mobile@upi"
                    />
                    <button
                      type="button"
                      onClick={copyVpa}
                      style={{
                        background: 'rgba(255,255,255,0.06)',
                        border: '1px solid rgba(255,255,255,0.12)',
                        borderRadius: 8,
                        padding: '0 10px',
                        color: copiedVpa ? '#22c55e' : 'rgba(255,255,255,0.7)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                        fontSize: 11,
                      }}
                    >
                      {copiedVpa ? <Check size={12} /> : <Copy size={12} />}
                      {copiedVpa ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* TAB: CARDS */}
            {activeTab === 'card' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', display: 'block', marginBottom: 4 }}>
                    Card Number
                  </label>
                  <input
                    type="text"
                    value={cardNumber}
                    onChange={(e) => setCardNumber(e.target.value)}
                    style={{
                      width: '100%',
                      background: 'rgba(255,255,255,0.04)',
                      border: '1px solid rgba(255,255,255,0.12)',
                      borderRadius: 8,
                      padding: '9px 12px',
                      color: '#fff',
                      fontSize: 13,
                      letterSpacing: 1,
                      fontFamily: 'monospace',
                    }}
                  />
                  <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginTop: 3, display: 'block' }}>
                    Demo cards: Visa, Mastercard, RuPay
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div>
                    <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', display: 'block', marginBottom: 4 }}>
                      Valid Thru (MM/YY)
                    </label>
                    <input
                      type="text"
                      value={expiry}
                      onChange={(e) => setExpiry(e.target.value)}
                      style={{
                        width: '100%',
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.12)',
                        borderRadius: 8,
                        padding: '9px 12px',
                        color: '#fff',
                        fontSize: 13,
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', display: 'block', marginBottom: 4 }}>
                      CVV
                    </label>
                    <input
                      type="password"
                      maxLength={4}
                      value={cvv}
                      onChange={(e) => setCvv(e.target.value)}
                      style={{
                        width: '100%',
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.12)',
                        borderRadius: 8,
                        padding: '9px 12px',
                        color: '#fff',
                        fontSize: 13,
                      }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* TAB: NETBANKING */}
            {activeTab === 'netbanking' && (
              <div>
                <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', display: 'block', marginBottom: 8 }}>
                  Select Bank
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
                  {['HDFC Bank', 'ICICI Bank', 'State Bank of India', 'Axis Bank', 'Kotak Mahindra', 'Punjab National Bank'].map((bank) => (
                    <button
                      key={bank}
                      type="button"
                      onClick={() => setSelectedBank(bank)}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 8,
                        border:
                          selectedBank === bank
                            ? '1px solid #3395ff'
                            : '1px solid rgba(255,255,255,0.08)',
                        background:
                          selectedBank === bank
                            ? 'rgba(51, 149, 255, 0.12)'
                            : 'rgba(255,255,255,0.03)',
                        color: selectedBank === bank ? '#3395ff' : '#cbd5e1',
                        fontSize: 12,
                        textAlign: 'left',
                        cursor: 'pointer',
                        fontWeight: selectedBank === bank ? 600 : 400,
                      }}
                    >
                      {bank}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Pay CTA Button */}
            <button
              onClick={handlePay}
              disabled={paymentState === 'processing'}
              style={{
                width: '100%',
                marginTop: 20,
                padding: '13px 20px',
                borderRadius: 12,
                border: 'none',
                background:
                  paymentState === 'processing'
                    ? '#1e293b'
                    : 'linear-gradient(135deg, #3395ff 0%, #0052cc 100%)',
                color: '#ffffff',
                fontSize: 14,
                fontWeight: 700,
                cursor: paymentState === 'processing' ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                boxShadow:
                  paymentState === 'processing'
                    ? 'none'
                    : '0 6px 20px rgba(51,149,255,0.35)',
                transition: 'all 0.2s ease',
              }}
            >
              {paymentState === 'processing' ? (
                <>
                  <div
                    style={{
                      width: 16,
                      height: 16,
                      border: '2px solid rgba(255,255,255,0.3)',
                      borderTopColor: '#3395ff',
                      borderRadius: '50%',
                      animation: 'spin 0.8s linear infinite',
                    }}
                  />
                  <span>Connecting with Bank...</span>
                </>
              ) : (
                <>
                  <Lock size={14} />
                  <span>Pay ₹{formattedAmount} Now</span>
                </>
              )}
            </button>

            {/* Security note */}
            <div
              style={{
                textAlign: 'center',
                marginTop: 14,
                fontSize: 11,
                color: 'rgba(255,255,255,0.35)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
              }}
            >
              <Shield size={12} color="#22c55e" />
              <span>PCI-DSS Level 1 Compliant • Secured by Razorpay</span>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
