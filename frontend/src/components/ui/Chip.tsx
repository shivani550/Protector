import React from 'react';
import { CheckCircle2, AlertTriangle, Clock, XCircle, Info, HelpCircle } from 'lucide-react';

export type ChipVariant = 
  | 'covered' 
  | 'delivered' 
  | 'sent' 
  | 'needs_document' 
  | 'queued' 
  | 'processing' 
  | 'reply_needed' 
  | 'failed' 
  | 'neutral'
  | 'violet';

interface ChipProps {
  label: string;
  variant?: ChipVariant;
  icon?: React.ReactNode;
  className?: string;
  size?: 'sm' | 'md';
}

export const Chip: React.FC<ChipProps> = ({
  label,
  variant = 'neutral',
  icon,
  className = '',
  size = 'md',
}) => {
  const getStylesAndDefaultIcon = () => {
    switch (variant) {
      case 'covered':
      case 'delivered':
      case 'sent':
        return {
          bg: 'bg-cf-success-bg text-cf-success border-cf-success/30',
          defaultIcon: <CheckCircle2 className="w-3.5 h-3.5 text-cf-success flex-shrink-0" />,
        };
      case 'needs_document':
        return {
          bg: 'bg-cf-warn-bg text-cf-warn border-cf-warn/30',
          defaultIcon: <AlertTriangle className="w-3.5 h-3.5 text-cf-warn flex-shrink-0" />,
        };
      case 'queued':
      case 'processing':
        return {
          bg: 'bg-cf-lavender text-cf-violet-700 border-cf-thistle',
          defaultIcon: <Clock className="w-3.5 h-3.5 text-cf-violet-600 flex-shrink-0 animate-spin" />,
        };
      case 'reply_needed':
        return {
          bg: 'bg-cf-info-bg text-cf-violet-700 border-cf-plum/40',
          defaultIcon: <HelpCircle className="w-3.5 h-3.5 text-cf-violet-600 flex-shrink-0" />,
        };
      case 'failed':
        return {
          bg: 'bg-cf-danger-bg text-cf-danger border-cf-danger/30',
          defaultIcon: <XCircle className="w-3.5 h-3.5 text-cf-danger flex-shrink-0" />,
        };
      case 'violet':
        return {
          bg: 'bg-cf-violet-900 text-cf-thistle border-cf-violet-700',
          defaultIcon: <Info className="w-3.5 h-3.5 text-cf-plum flex-shrink-0" />,
        };
      case 'neutral':
      default:
        return {
          bg: 'bg-cf-bg-2 text-cf-text-2 border-cf-border',
          defaultIcon: null,
        };
    }
  };

  const { bg, defaultIcon } = getStylesAndDefaultIcon();
  const sizeClasses = size === 'sm' 
    ? 'text-[11px] px-2.5 py-0.5 gap-1' 
    : 'text-xs px-3 py-1 gap-1.5';

  return (
    <span
      className={`inline-flex items-center font-head font-medium rounded-full border transition-colors ${bg} ${sizeClasses} ${className}`}
    >
      {icon || defaultIcon}
      <span>{label}</span>
    </span>
  );
};
