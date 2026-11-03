import React from 'react';
import { Check, Loader2 } from 'lucide-react';

interface StepperProps {
  status: string; // 'received' | 'extracting' | 'matching' | 'composing' | 'sending' | 'completed' | 'failed' | 'needs_review'
  claimRef?: string;
  totalMs?: number;
  neededCount?: number;
}

export const Stepper: React.FC<StepperProps> = ({ status, claimRef, totalMs, neededCount = 0 }) => {
  const steps = [
    { key: 'extracting', label: 'Reading letter & OCR' },
    { key: 'matching', label: 'Checking locker documents' },
    { key: 'composing', label: 'Writing plain message' },
    { key: 'sending', label: 'Dispatching WhatsApp & Email' },
    { key: 'completed', label: 'Done & Verified' },
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
  const isTerminal = ['completed', 'failed', 'needs_review'].includes(status);
  const isSuccess = status === 'completed';
  const hasMissingDocs = isSuccess && neededCount > 0;

  return (
    <div 
      className="p-5 rounded-cf-lg border border-cf-border-2 bg-cf-surface shadow-card mb-6"
      aria-live="polite"
      role="region"
      aria-label="Query Letter Autonomous Processing Status"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${hasMissingDocs ? 'bg-cf-warn' : 'bg-cf-violet-600'} animate-pulse`} />
            <span className="text-xs font-head font-semibold uppercase tracking-wider text-cf-steel">
              Autonomous Pipeline Stepper
            </span>
          </div>
          <h3 className="text-base font-head font-bold text-cf-violet-900 mt-0.5">
            {hasMissingDocs 
              ? 'Action Needed: Missing Documents Requested via WhatsApp & Email' 
              : isSuccess 
              ? 'Query Letter Resolved with Zero False Asks — All Covered' 
              : 'Autonomous Query Resolution in Flight'}
          </h3>
          <p className="text-xs font-body text-cf-text-2 mt-0.5">
            Claim Ref: <span className="font-mono font-medium text-cf-violet-700">{claimRef || 'CLM-XXXX'}</span>
            {totalMs ? ` · Completed in ${totalMs} ms` : ''}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-xs font-head font-semibold ${
            hasMissingDocs ? 'bg-cf-warn-bg text-cf-warn border border-cf-warn/30' :
            isSuccess ? 'bg-cf-success-bg text-cf-success border border-cf-success/30' :
            status === 'failed' ? 'bg-cf-danger-bg text-cf-danger border border-cf-danger/30' :
            status === 'needs_review' ? 'bg-cf-warn-bg text-cf-warn border border-cf-warn/30' :
            'bg-cf-lavender text-cf-violet-700 border border-cf-plum/40'
          }`}>
            {hasMissingDocs ? 'NEEDS DOCUMENT' : isSuccess ? 'COVERED' : status.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Stepper Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5 pt-3 border-t border-cf-border">
        {steps.map((st, idx) => {
          const stepNum = idx + 1;
          const isDone = currentIndex > stepNum || (isSuccess && stepNum === 5);
          const isCurrent = currentIndex === stepNum && !isTerminal;

          return (
            <div
              key={st.key}
              className={`p-3 rounded-cf-md border text-xs font-head transition-all flex items-center gap-2.5 ${
                isDone 
                  ? 'bg-cf-success-bg text-cf-success border-cf-success/20' 
                  : isCurrent 
                  ? 'bg-cf-info-bg text-cf-violet-900 border-cf-violet-600 shadow-xs' 
                  : 'bg-cf-surface-2 text-cf-muted border-cf-border'
              }`}
            >
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                isDone 
                  ? 'bg-cf-success text-white' 
                  : isCurrent 
                  ? 'bg-cf-violet-600 text-white animate-pulse' 
                  : 'bg-cf-border text-cf-muted'
              }`}>
                {isDone ? <Check className="w-3.5 h-3.5" /> : isCurrent ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : stepNum}
              </span>
              <span className="truncate font-medium">{st.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
