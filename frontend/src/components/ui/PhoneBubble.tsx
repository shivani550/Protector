import React, { useState } from 'react';
import { MessageSquare, Mail, CheckCheck, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import { OutboundMessage } from '../../types';

interface PhoneBubbleProps {
  message: OutboundMessage;
}

export const PhoneBubble: React.FC<PhoneBubbleProps> = ({ message }) => {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const isWhatsApp = message.channel === 'whatsapp';

  const handleCopy = () => {
    navigator.clipboard.writeText(message.body_rendered);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-cf-border-2 rounded-cf-md bg-cf-surface shadow-card overflow-hidden transition-all duration-200">
      {/* Header bar */}
      <div 
        onClick={() => setExpanded(!expanded)}
        className="p-4 flex items-center justify-between cursor-pointer hover:bg-cf-bg transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-cf-sm flex items-center justify-center flex-shrink-0 ${
            isWhatsApp ? 'bg-[#25D366]/15 text-[#075E54]' : 'bg-cf-info-bg text-cf-violet-700'
          }`}>
            {isWhatsApp ? <MessageSquare className="w-4 h-4" /> : <Mail className="w-4 h-4" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-head font-bold text-sm text-cf-text uppercase">
                {isWhatsApp ? 'WhatsApp Dispatch' : 'Email Dispatch'}
              </span>
              <span className="text-xs font-mono text-cf-text-3">
                ({message.recipient_masked})
              </span>
            </div>
            <div className="text-[11px] font-body text-cf-muted">
              Queued at {new Date(message.queued_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • Template v{message.template_version}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-head font-semibold uppercase ${
            message.status === 'sent' || message.status === 'delivered'
              ? 'bg-cf-success-bg text-cf-success'
              : message.status === 'failed'
              ? 'bg-cf-danger-bg text-cf-danger'
              : 'bg-cf-lavender text-cf-violet-700'
          }`}>
            {message.status}
          </span>
          <button className="text-cf-muted hover:text-cf-violet-700 p-1">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expandable Preview */}
      {expanded && (
        <div className="p-4 border-t border-cf-border bg-cf-bg-2">
          {isWhatsApp ? (
            /* WhatsApp Phone Bubble Mock */
            <div className="max-w-md mx-auto bg-[#efeae2] p-4 rounded-cf-lg border border-cf-border shadow-xs">
              <div className="bg-[#e7f8e8] border border-[#d2edd4] rounded-cf-md rounded-tr-none p-3.5 shadow-xs text-xs font-body text-[#111b21] whitespace-pre-wrap leading-relaxed relative">
                {message.body_rendered}
                <div className="flex items-center justify-end gap-1 mt-2 text-[10px] text-[#667781]">
                  <span>{new Date(message.queued_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  <CheckCheck className="w-3.5 h-3.5 text-[#53bdeb]" />
                </div>
              </div>
            </div>
          ) : (
            /* Email Card Mock */
            <div className="max-w-lg mx-auto bg-white rounded-cf-md border border-cf-border shadow-xs overflow-hidden">
              <div className="p-3 bg-cf-bg border-b border-cf-border text-xs">
                <div className="font-semibold text-cf-text">Subject: Urgent: Insurance Query Documents Required</div>
                <div className="text-[11px] text-cf-muted mt-0.5">From: Care.fi Health Desk &lt;claims@carefi.in&gt;</div>
              </div>
              <div className="p-4 text-xs font-body text-cf-text-2 whitespace-pre-wrap leading-relaxed">
                {message.body_rendered}
              </div>
            </div>
          )}

          <div className="mt-3 flex items-center justify-between text-[11px] text-cf-muted px-1">
            <span>Idempotency Key: <code className="font-mono text-cf-text-3">{message.idempotency_key?.slice(0, 18)}...</code></span>
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1 text-cf-violet-600 hover:text-cf-violet-900 font-head font-medium"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-cf-success" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy Text'}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
