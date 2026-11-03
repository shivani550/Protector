import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  Upload, CheckCircle2, AlertTriangle, FileText, 
  Camera, Lock, ArrowRight, RefreshCw, Check
} from 'lucide-react';
import { api } from '../api';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';

export default function MagicUpload() {
  const { token } = useParams<{ token: string }>();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<any | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Fetch token context
  const { data: uploadInfo, isLoading, error } = useQuery({
    queryKey: ['magic-upload', token],
    queryFn: () => api.getMagicUploadInfo(token!),
    enabled: !!token,
    retry: 1,
  });

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !selectedFile) return;

    setUploading(true);
    setUploadError(null);
    try {
      const res = await api.submitMagicUpload(token, selectedFile);
      setUploadSuccess(res);
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center p-4">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-cf-violet-600/30 border-t-cf-violet-600 rounded-full animate-spin mx-auto mb-3" />
          <p className="text-xs font-head font-medium text-cf-text-2">Verifying secure Care.fi upload token...</p>
        </div>
      </div>
    );
  }

  if (error || !uploadInfo) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center p-4">
        <Card className="p-8 max-w-md w-full text-center">
          <div className="w-12 h-12 rounded-cf-md bg-cf-danger-bg text-cf-danger flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-head font-bold text-cf-violet-900 mb-1">Invalid or Expired Link</h2>
          <p className="text-xs font-body text-cf-text-2 mb-6">
            This secure upload link is no longer valid or has expired. Please check your latest WhatsApp or Email message for a fresh link.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-[85vh] flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Care.fi Branded Upload Card */}
        <Card className="p-6 sm:p-8 shadow-card border border-cf-border-2">
          {/* Header */}
          <div className="flex items-center gap-3 pb-5 border-b border-cf-border mb-5">
            <div className="w-11 h-11 rounded-cf-sm bg-cf-lavender text-cf-violet-900 flex items-center justify-center flex-shrink-0">
              <Upload className="w-5 h-5 text-cf-violet-700" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-head font-bold text-base text-cf-violet-900 tracking-tight">
                  Care.fi Document Deposit
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-head font-semibold bg-cf-info-bg text-cf-violet-700">
                  Instant Match
                </span>
              </div>
              <p className="text-xs font-body text-cf-text-2">
                Hi <strong className="text-cf-violet-900">{uploadInfo.patient_first_name}</strong>, your claim with <strong className="text-cf-violet-900">{uploadInfo.insurer_name}</strong> needs documents
              </p>
            </div>
          </div>

          {uploadSuccess ? (
            /* Final Success State: All set, thank you! */
            <div className="text-center py-6">
              <div className="w-16 h-16 rounded-full bg-cf-success-bg text-cf-success flex items-center justify-center mx-auto mb-4 border border-cf-success/30">
                <Check className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-head font-bold text-cf-violet-900 mb-1">All set, thank you!</h2>
              <p className="text-xs font-body text-cf-text-2 mb-6 max-w-sm mx-auto leading-relaxed">
                Your file <code className="bg-cf-bg px-2 py-0.5 rounded text-[11px] font-mono text-cf-violet-900 font-semibold">{uploadSuccess.filename}</code> has been classified as{' '}
                <strong className="text-cf-success">{uploadSuccess.classified_as}</strong> and vaulted into your claim.
              </p>
              <div className="p-4 rounded-cf-md bg-cf-bg-2 border border-cf-border text-xs font-body text-cf-text-2 max-w-sm mx-auto">
                No further action is required from you. The Care.fi engine has updated your query resolution record.
              </div>
            </div>
          ) : (
            <form onSubmit={handleUploadSubmit} className="space-y-5">
              {/* Requested Document Types Cards */}
              <div className="p-4 rounded-cf-md bg-cf-warn-bg/60 border border-cf-warn/30">
                <span className="text-xs font-head font-bold text-cf-warn block mb-1.5 uppercase tracking-wider">
                  Requested by {uploadInfo.insurer_name}
                </span>
                <p className="text-xs font-body text-cf-text-2 mb-2.5">
                  Please provide one of the following documents to resolve the inquiry:
                </p>
                <div className="flex flex-wrap gap-2">
                  {uploadInfo.requested_documents?.map((doc: any, i: number) => (
                    <span 
                      key={i} 
                      className="px-2.5 py-1 rounded-full bg-white border border-cf-warn/30 text-cf-warn font-head text-xs font-semibold shadow-xs"
                    >
                      {typeof doc === 'string' ? doc : doc.doc_type || 'Document'}
                    </span>
                  ))}
                </div>
              </div>

              {uploadError && (
                <div className="p-3.5 rounded-cf-sm bg-cf-danger-bg border border-cf-danger/30 text-cf-danger text-xs font-body flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}

              {/* Upload Drop / Pick Zone */}
              <div className="border-2 border-dashed border-cf-plum/60 hover:border-cf-violet-600 rounded-cf-lg p-6 text-center cursor-pointer transition-colors bg-cf-bg-2 hover:bg-cf-lavender/30">
                <input
                  type="file"
                  id="magic-file"
                  required
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="hidden"
                />
                <label htmlFor="magic-file" className="cursor-pointer block">
                  <div className="w-12 h-12 rounded-cf-md bg-cf-surface shadow-xs border border-cf-border text-cf-violet-600 flex items-center justify-center mx-auto mb-3">
                    <Camera className="w-6 h-6" />
                  </div>
                  {selectedFile ? (
                    <div>
                      <span className="text-sm font-head font-bold text-cf-violet-900 block truncate max-w-xs mx-auto">
                        {selectedFile.name}
                      </span>
                      <span className="text-xs font-body text-cf-muted">
                        {Math.round(selectedFile.size / 1024)} KB • Ready to submit
                      </span>
                    </div>
                  ) : (
                    <div>
                      <span className="text-sm font-head font-bold text-cf-text block">
                        Tap to take a photo or select file
                      </span>
                      <span className="text-xs font-body text-cf-muted mt-1 block">
                        PDF, PNG, JPG accepted (up to 25MB)
                      </span>
                    </div>
                  )}
                </label>
              </div>

              {/* Submit button */}
              <Button
                type="submit"
                variant="primary"
                disabled={!selectedFile || uploading}
                loading={uploading}
                className="w-full"
              >
                <span>Deposit Document</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            </form>
          )}

          {/* Security note */}
          <div className="mt-6 pt-5 border-t border-cf-border flex items-center justify-center gap-1.5 text-cf-muted text-xs font-body">
            <Lock className="w-3.5 h-3.5" />
            <span>256-bit Encrypted • Direct Care.fi Vault Pipeline</span>
          </div>
        </Card>
      </div>
    </div>
  );
}
