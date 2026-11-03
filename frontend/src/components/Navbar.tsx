import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Activity, LogOut, Radio, PhoneCall, HelpCircle } from 'lucide-react';
import { api } from '../api';
import { User } from '../types';

interface NavbarProps {
  user: User | null;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [sseConnected, setSseConnected] = useState(false);

  useEffect(() => {
    const evtSource = new EventSource('/api/events');
    evtSource.onopen = () => setSseConnected(true);
    evtSource.onerror = () => setSseConnected(false);
    return () => evtSource.close();
  }, []);

  const handleLogout = async () => {
    await api.logout();
    onLogout();
    navigate('/login');
  };

  if (!user) return null;

  return (
    <header className="border-b bg-cf-surface border-cf-border sticky top-0 z-40 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand with Care.fi Logo */}
        <div className="flex items-center gap-8">
          <Link to={user.role === 'patient' ? '/me' : '/patients'} className="flex items-center gap-2">
            {/* Inline SVG Brand Logo */}
            <svg viewBox="0 0 190 40" fill="none" className="h-8 w-auto">
              <rect x="2" y="4" width="32" height="32" rx="9" fill="#644790" />
              <circle cx="15" cy="17" r="4.5" fill="#b6a7de" />
              <path d="M11 27C11 23 14 20 18 20C22 20 25 23 25 27" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" />
              <circle cx="25" cy="14" r="2.5" fill="#269d72" />
              <text x="42" y="27" fontFamily="'Poppins', sans-serif" fontWeight="700" fontSize="21" fill="#111111" letterSpacing="-0.5">Care<tspan fill="#644790">.fi</tspan></text>
              <rect x="115" y="11" width="60" height="20" rx="10" fill="#e4e0f4" />
              <text x="145" y="25" fontFamily="'Poppins', sans-serif" fontWeight="600" fontSize="10.5" fill="#644790" textAnchor="middle" letterSpacing="0.3">LOCKER</text>
            </svg>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1.5">
            {user.role !== 'patient' && (
              <Link
                to="/patients"
                className={`px-3.5 py-1.5 rounded-cf-sm text-xs font-head font-medium transition-colors ${
                  location.pathname.startsWith('/patients')
                    ? 'bg-cf-lavender text-cf-violet-900 font-semibold'
                    : 'text-cf-text-2 hover:text-cf-violet-900 hover:bg-cf-bg-2'
                }`}
              >
                Patients
              </Link>
            )}
            {user.role === 'admin' && (
              <Link
                to="/admin"
                className={`px-3.5 py-1.5 rounded-cf-sm text-xs font-head font-medium transition-colors flex items-center gap-1.5 ${
                  location.pathname === '/admin'
                    ? 'bg-cf-lavender text-cf-violet-900 font-semibold'
                    : 'text-cf-text-2 hover:text-cf-violet-900 hover:bg-cf-bg-2'
                }`}
              >
                <Activity className="w-3.5 h-3.5 text-cf-violet-600" />
                Pipeline Admin
              </Link>
            )}
            {user.role === 'patient' && (
              <Link
                to="/me"
                className={`px-3.5 py-1.5 rounded-cf-sm text-xs font-head font-medium transition-colors ${
                  location.pathname === '/me'
                    ? 'bg-cf-lavender text-cf-violet-900 font-semibold'
                    : 'text-cf-text-2 hover:text-cf-violet-900 hover:bg-cf-bg-2'
                }`}
              >
                My Locker
              </Link>
            )}
          </nav>
        </div>

        {/* Right Status & Actions */}
        <div className="flex items-center gap-3">
          {/* Live SSE indicator */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-head bg-cf-bg-2 border border-cf-border">
            <Radio className={`w-3 h-3 ${sseConnected ? 'text-cf-success animate-pulse' : 'text-cf-muted'}`} />
            <span className={sseConnected ? 'text-cf-success font-medium' : 'text-cf-muted'}>
              {sseConnected ? 'Real-Time Sync' : 'Syncing'}
            </span>
          </div>

          {/* Pill "Need help?" Button */}
          <a
            href="tel:18001234567"
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-head font-medium bg-cf-info-bg text-cf-violet-900 hover:bg-cf-lavender transition-colors"
            title="Helpline: 1800-123-4567"
          >
            <PhoneCall className="w-3 h-3 text-cf-violet-600" />
            <span>Need help?</span>
          </a>

          {/* User Role Badge */}
          <div className="flex items-center gap-2 pl-2 border-l border-cf-border">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-head font-semibold text-cf-text">{user.email}</div>
              <div className="text-[10px] font-head text-cf-muted uppercase tracking-wider">{user.role.replace('_', ' ')}</div>
            </div>
            <span className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-head font-bold shadow-xs ${
              user.role === 'admin' ? 'bg-cf-violet-600 text-white' :
              user.role === 'case_worker' ? 'bg-cf-steel text-white' : 'bg-cf-plum text-cf-violet-900'
            }`}>
              {user.email[0].toUpperCase()}
            </span>
          </div>

          {/* Logout button */}
          <button
            onClick={handleLogout}
            title="Log out"
            className="p-2 text-cf-text-3 hover:text-cf-violet-900 rounded-cf-sm hover:bg-cf-bg-2 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
