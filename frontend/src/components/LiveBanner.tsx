import React from 'react';
import { CheckCircle2, Clock, AlertTriangle, XCircle, ArrowRight, Loader2 } from 'lucide-react';

interface LiveBannerProps {
  status: string;
  claimRef?: string;
  totalMs?: number;
}

export const LiveBanner: React.FC<LiveBannerProps> = ({ status, claimRef, totalMs }) => {
  const isTerminal = ['completed', 'failed', 'needs_review'].includes(status);
  const isSuccess = status === 'completed';
  const isNeedsReview = status === 'needs_review';
  const isFailed = status === 'failed';

  const steps = [
    { key: 'extracting', label: 'Reading letter & OCR' },
    { key: 'matching', label: 'Checking locker documents' },
    { key: 'composing', label: 'Writing plain messages' },
    { key: 'sending', label: 'Sending WhatsApp & Email' },
  ];

  const getStepIndex = (s: string) => {
    switch (s) {
      case 'received': return 0;
      case 'extracting': return 1;
      case 'matching': return 2;
      case 'composing': return 3;
      case 'sending': return 4;
      case 'completed': return 5;
      default: return 0;
    }
  };

  const currentIndex = getStepIndex(status);

  return (
    <div className={`p-4 rounded-xl border mb-6 transition-all duration-300 ${
      isSuccess ? 'bg-emerald-50/70 border-emerald-200' :
      isNeedsReview ? 'bg-amber-50/70 border-amber-200' :
      isFailed ? 'bg-rose-50/70 border-rose-200' :
      'bg-sky-50/80 border-sky-200 shadow-xs'
    }`}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5">
          {!isTerminal ? (
            <span className="w-6 h-6 rounded-full bg-sky-600 text-white flex items-center justify-center animate-spin">
              <Loader2 className="w-3.5 h-3.5" />
            </span>
          ) : isSuccess ? (
            <CheckCircle2 className="w-6 h-6 text-emerald-600" />
          ) : isNeedsReview ? (
            <AlertTriangle className="w-6 h-6 text-amber-600" />
          ) : (
            <XCircle className="w-6 h-6 text-rose-600" />
          )}

          <div>
            <h4 className="text-sm font-bold text-slate-900 leading-tight">
              {!isTerminal && 'Autonomous Query Processing in Progress'}
              {isSuccess && 'Autonomous Query Resolution Completed'}
              {isNeedsReview && 'Query Letter Requires Staff Glance'}
              {isFailed && 'Query Processing Failed'}
            </h4>
            <p className="text-xs text-slate-600 mt-0.5">
              Claim Ref: <span className="font-mono font-medium">{claimRef || 'CLAIM'}</span>
              {totalMs ? ` · Processed in ${totalMs} ms` : ''}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
            isSuccess ? 'bg-emerald-100 text-emerald-800' :
            isNeedsReview ? 'bg-amber-100 text-amber-800' :
            isFailed ? 'bg-rose-100 text-rose-800' :
            'bg-sky-100 text-sky-800 animate-pulse'
          }`}>
            {status}
          </span>
        </div>
      </div>

      {/* Progress pipeline steps */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-200/60">
        {steps.map((st, idx) => {
          const stepNum = idx + 1;
          const isDone = currentIndex > stepNum || isSuccess;
          const isCurrent = currentIndex === stepNum && !isTerminal;

          return (
            <div
              key={st.key}
              className={`p-2 rounded-lg text-xs font-semibold flex items-center gap-2 ${
                isDone ? 'bg-emerald-100/60 text-emerald-800 border border-emerald-200/50' :
                isCurrent ? 'bg-sky-100 text-sky-900 border border-sky-300 shadow-xs' :
                'bg-white/60 text-slate-400 border border-slate-200/40'
              }`}
            >
              <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                isDone ? 'bg-emerald-600 text-white' :
                isCurrent ? 'bg-sky-600 text-white animate-pulse' :
                'bg-slate-200 text-slate-500'
              }`}>
                {isDone ? '✓' : stepNum}
              </span>
              <span className="truncate">{st.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
