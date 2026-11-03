import React from 'react';
import { ShieldCheck, Heart } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-cf-violet-900 border-t border-cf-violet-700 text-cf-thistle mt-12 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        {/* Brand & Sibling Lines */}
        <div>
          <div className="flex items-center gap-2">
            <span className="font-head font-bold text-lg text-white tracking-tight">
              Care<span className="text-cf-plum">.fi</span>
            </span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-head font-semibold bg-white/10 text-cf-plum border border-white/10">
              LOCKER
            </span>
          </div>
          <p className="text-xs text-cf-thistle/80 mt-1 max-w-sm font-body">
            India's autonomous patient locker & insurance query resolution engine. Sibling product of RevNow and CareCred.
          </p>
        </div>

        {/* Product Navigation */}
        <div className="flex flex-wrap items-center gap-6 text-xs font-head font-medium text-cf-thistle">
          <a href="https://carefi.in" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">
            RevNow (Smart RCM)
          </a>
          <a href="https://carefi.in" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">
            CareCred (Financing)
          </a>
          <span className="text-white font-semibold underline decoration-cf-plum decoration-2 underline-offset-4">
            Locker
          </span>
          <span className="text-white/20">|</span>
          <a href="mailto:support@carefi.in" className="hover:text-white transition-colors">
            support@carefi.in
          </a>
          <a href="#privacy" className="hover:text-white transition-colors">
            Privacy Policy
          </a>
          <a href="#terms" className="hover:text-white transition-colors">
            Terms of Use
          </a>
        </div>
      </div>

      <div className="max-w-7xl mx-auto pt-6 mt-6 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between text-[11px] text-cf-thistle/60 font-body gap-2">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-cf-success" />
          <span>Fernet-256 AES Encrypted • HIPAA & DPDP Compliant Data Vault</span>
        </div>
        <div>
          © {new Date().getFullYear()} Care.fi Healthcare Technologies. All rights reserved.
        </div>
      </div>
    </footer>
  );
};
