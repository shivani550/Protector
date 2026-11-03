import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail, ArrowRight, UserCheck, Stethoscope, User, AlertCircle, CheckCircle2 } from 'lucide-react';
import { api } from '../api';
import { Button } from '../components/ui/Button';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.login(email, password);
      const user = await api.getMe();
      localStorage.setItem('user', JSON.stringify(user));
      
      if (user.role === 'patient') {
        navigate('/me');
      } else {
        navigate('/patients');
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (quickEmail: string, quickPass: string) => {
    setEmail(quickEmail);
    setPassword(quickPass);
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center p-4">
      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-12 rounded-cf-xl overflow-hidden shadow-card border border-cf-border-2 bg-cf-surface">
        
        {/* Left: Care.fi Dark Brand Panel */}
        <div className="lg:col-span-6 bg-cf-violet-900 p-8 sm:p-12 flex flex-col justify-between relative overflow-hidden text-white">
          <div className="absolute inset-0 bg-gradient-to-br from-black/40 via-transparent to-cf-violet-700/30 pointer-events-none" />

          {/* Top Wordmark */}
          <div className="relative z-10 flex items-center gap-2.5 mb-8">
            <svg viewBox="0 0 190 40" fill="none" className="h-8 w-auto">
              <rect x="2" y="4" width="32" height="32" rx="9" fill="#8275ab" />
              <circle cx="15" cy="17" r="4.5" fill="#b6a7de" />
              <path d="M11 27C11 23 14 20 18 20C22 20 25 23 25 27" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" />
              <circle cx="25" cy="14" r="2.5" fill="#269d72" />
              <text x="42" y="27" fontFamily="'Poppins', sans-serif" fontWeight="700" fontSize="21" fill="#ffffff" letterSpacing="-0.5">Care<tspan fill="#b6a7de">.fi</tspan></text>
              <rect x="115" y="11" width="60" height="20" rx="10" fill="#644790" />
              <text x="145" y="25" fontFamily="'Poppins', sans-serif" fontWeight="600" fontSize="10.5" fill="#e4e0f4" textAnchor="middle" letterSpacing="0.3">LOCKER</text>
            </svg>
          </div>

          {/* Headline with Georgia Serif Accent */}
          <div className="relative z-10 my-auto py-6">
            <h1 className="font-head text-3xl sm:text-4xl font-bold tracking-tight leading-tight text-white">
              Your documents.<br />
              Your <span className="font-serif italic font-normal text-cf-plum">claim</span>.<br />
              Always in sync.
            </h1>
            <p className="font-body text-sm text-cf-thistle mt-3 max-w-md leading-relaxed">
              Auto-answering insurer queries in minutes. Powered by Care.fi’s healthcare revenue and locker intelligence.
            </p>

            {/* Trust Bullets */}
            <div className="mt-8 space-y-3 font-body text-xs text-cf-thistle/90">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-cf-success flex-shrink-0" />
                <span>Zero False Asks: never prompted for documents already vaulted</span>
              </div>
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-cf-success flex-shrink-0" />
                <span>Autonomous dual-channel dispatch to WhatsApp and Email</span>
              </div>
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-cf-success flex-shrink-0" />
                <span>Fernet-256 AES encryption & DPDP data compliance</span>
              </div>
            </div>
          </div>

          {/* Scrolling Ticker */}
          <div className="relative z-10 mt-8 pt-6 border-t border-white/10 overflow-hidden text-[11px] font-head text-cf-thistle/70 uppercase tracking-widest whitespace-nowrap">
            <div className="cf-animate-ticker flex gap-8">
              <span>Auto-Read Letters</span>
              <span>·</span>
              <span>Locker Matching</span>
              <span>·</span>
              <span>Zero False Asks</span>
              <span>·</span>
              <span>Instant Dispatch</span>
              <span>·</span>
              <span>Auto-Read Letters</span>
              <span>·</span>
              <span>Locker Matching</span>
              <span>·</span>
              <span>Zero False Asks</span>
              <span>·</span>
              <span>Instant Dispatch</span>
            </div>
          </div>
        </div>

        {/* Right: Login Form */}
        <div className="lg:col-span-6 p-8 sm:p-12 flex flex-col justify-center bg-cf-surface">
          <div className="max-w-sm w-full mx-auto">
            <div className="mb-6">
              <h2 className="font-head text-2xl font-bold text-cf-text tracking-tight">
                Sign In
              </h2>
              <p className="font-body text-xs text-cf-text-2 mt-1">
                Enter your credentials to access the Care.fi Locker platform
              </p>
            </div>

            {error && (
              <div className="mb-5 p-3.5 rounded-cf-sm bg-cf-danger-bg border border-cf-danger/30 flex items-start gap-3 text-cf-danger text-xs font-body">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block font-head text-xs font-semibold text-cf-text-2 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-cf-muted absolute left-3.5 top-3.5 pointer-events-none" />
                  <input
                    type="email"
                    required
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="cf-input w-full pl-10 pr-4 py-2.5 text-xs font-body"
                  />
                </div>
              </div>

              <div>
                <label className="block font-head text-xs font-semibold text-cf-text-2 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-cf-muted absolute left-3.5 top-3.5 pointer-events-none" />
                  <input
                    type="password"
                    required
                    placeholder="••••••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="cf-input w-full pl-10 pr-4 py-2.5 text-xs font-body"
                  />
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                loading={loading}
                className="w-full mt-2"
              >
                <span>Sign In to Locker</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            </form>

            {/* Quick Demo Role Buttons */}
            <div className="mt-8 pt-6 border-t border-cf-border">
              <p className="font-head text-[11px] font-semibold uppercase tracking-wider text-cf-muted mb-3 text-center">
                Quick Fill Demo Accounts
              </p>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => handleQuickLogin('admin@demo.test', 'DemoPass123!')}
                  className="flex flex-col items-center justify-center p-2.5 rounded-cf-sm border border-cf-border hover:border-cf-plum hover:bg-cf-bg-2 transition-all group"
                >
                  <div className="w-7 h-7 rounded-cf-sm bg-cf-info-bg text-cf-violet-700 flex items-center justify-center mb-1 group-hover:scale-105 transition-transform">
                    <UserCheck className="w-4 h-4" />
                  </div>
                  <span className="font-head text-xs font-semibold text-cf-text">Admin</span>
                  <span className="font-body text-[10px] text-cf-muted">Full Access</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickLogin('worker@demo.test', 'DemoPass123!')}
                  className="flex flex-col items-center justify-center p-2.5 rounded-cf-sm border border-cf-border hover:border-cf-plum hover:bg-cf-bg-2 transition-all group"
                >
                  <div className="w-7 h-7 rounded-cf-sm bg-cf-lavender text-cf-violet-900 flex items-center justify-center mb-1 group-hover:scale-105 transition-transform">
                    <Stethoscope className="w-4 h-4" />
                  </div>
                  <span className="font-head text-xs font-semibold text-cf-text">Worker</span>
                  <span className="font-body text-[10px] text-cf-muted">Assigned</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickLogin('patient1@demo.test', 'DemoPass123!')}
                  className="flex flex-col items-center justify-center p-2.5 rounded-cf-sm border border-cf-border hover:border-cf-plum hover:bg-cf-bg-2 transition-all group"
                >
                  <div className="w-7 h-7 rounded-cf-sm bg-cf-success-bg text-cf-success flex items-center justify-center mb-1 group-hover:scale-105 transition-transform">
                    <User className="w-4 h-4" />
                  </div>
                  <span className="font-head text-xs font-semibold text-cf-text">Patient</span>
                  <span className="font-body text-[10px] text-cf-muted">Arjun S.</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
