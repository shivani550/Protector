import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  ShieldCheck, FileText, CheckCircle2, Clock, Upload, 
  ExternalLink, Lock, Check
} from 'lucide-react';
import { api } from '../api';
import { Patient, Document, QueryLetter } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';

export default function PatientSelfPortal() {
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  // 1. Get Me (to get patient_id)
  const { data: user, isLoading: loadingUser } = useQuery({
    queryKey: ['me'],
    queryFn: api.getMe,
  });

  const patientId = user?.patient_id;

  // 2. Get Patient Info
  const { data: patient, isLoading: loadingPatient } = useQuery<Patient>({
    queryKey: ['my-patient', patientId],
    queryFn: () => api.getPatient(patientId!),
    enabled: !!patientId,
  });

  // 3. Get Documents
  const { data: documents, isLoading: loadingDocs, refetch: refetchDocs } = useQuery<Document[]>({
    queryKey: ['my-docs', patientId],
    queryFn: () => api.getPatientDocuments(patientId!),
    enabled: !!patientId,
  });

  // 4. Get Letters
  const { data: letters, isLoading: loadingLetters } = useQuery<QueryLetter[]>({
    queryKey: ['my-letters', patientId],
    queryFn: () => api.getPatientLetters(patientId!),
    enabled: !!patientId,
  });

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !patientId) return;
    setUploading(true);
    setUploadMessage(null);
    try {
      await api.uploadDocument(patientId, uploadFile, 'general');
      setUploadMessage('Document deposited securely into your health locker!');
      setUploadFile(null);
      refetchDocs();
    } catch (err: any) {
      setUploadMessage(`Upload error: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleView = async (docId: string) => {
    try {
      const res = await api.getDocumentSignedUrl(docId);
      window.open(res.url, '_blank');
    } catch (err: any) {
      alert(`Could not open document: ${err.message}`);
    }
  };

  if (loadingUser || loadingPatient) {
    return (
      <div className="p-16 text-center text-cf-muted">
        <div className="w-8 h-8 border-2 border-cf-violet-600/30 border-t-cf-violet-600 rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs font-head font-medium text-cf-text-2">Opening your personal health vault...</p>
      </div>
    );
  }

  const latestLetter = letters?.[0];
  const hasPendingAsks = latestLetter?.points?.some(p => p.decision?.decision === 'needs_new_document');

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Care.fi Brand Greeting Card */}
      <div className="bg-cf-violet-900 rounded-cf-xl p-6 sm:p-8 text-white shadow-card relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-black/40 via-transparent to-cf-violet-700/30 pointer-events-none" />

        <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 text-cf-plum text-xs font-head font-semibold backdrop-blur-md mb-3 border border-white/10">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Care.fi Verified Digital Locker</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-head font-bold tracking-tight">
              Hello, {patient?.full_name || 'Patient'}
            </h1>
            <p className="text-xs font-body text-cf-thistle mt-1.5 max-w-md leading-relaxed">
              Your personal health locker. We keep your hospital papers secure and resolve insurance queries automatically.
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-md rounded-cf-md p-4 border border-white/10 self-start sm:self-auto text-xs font-body">
            <span className="text-cf-thistle block font-head">Active Policy</span>
            <span className="font-head font-bold text-base block">{patient?.insurer_name}</span>
            <span className="font-mono text-cf-plum">{patient?.policy_number_masked}</span>
          </div>
        </div>
      </div>

      {/* Query Status Banner (Plain Language, Grade <= 6) */}
      <Card className="p-6">
        <h2 className="text-xs font-head font-bold uppercase tracking-wider text-cf-muted mb-2.5">
          Current Insurance Status
        </h2>

        {latestLetter ? (
          hasPendingAsks ? (
            <div className="flex items-start gap-3.5 p-4 rounded-cf-md bg-cf-warn-bg/70 border border-cf-warn/30 text-cf-warn">
              <Clock className="w-5 h-5 text-cf-warn flex-shrink-0 mt-0.5" />
              <div className="text-xs font-body">
                <strong className="block font-head font-semibold text-sm">Action Requested by {patient?.insurer_name}</strong>
                <p className="mt-1 text-cf-text-2 leading-relaxed">
                  Your insurance company has requested additional papers for your claim. Please check your WhatsApp or use the deposit box below to upload them.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-3.5 p-4 rounded-cf-md bg-cf-success-bg/70 border border-cf-success/30 text-cf-success">
              <CheckCircle2 className="w-5 h-5 text-cf-success flex-shrink-0 mt-0.5" />
              <div className="text-xs font-body">
                <strong className="block font-head font-semibold text-sm">All Questions Answered Automatically!</strong>
                <p className="mt-1 text-cf-text-2 leading-relaxed">
                  Your insurance company had questions, but Care.fi Locker verified all of them using records already in your vault. You do not need to do anything!
                </p>
              </div>
            </div>
          )
        ) : (
          <div className="flex items-start gap-3.5 p-4 rounded-cf-md bg-cf-bg-2 border border-cf-border text-cf-text-2">
            <CheckCircle2 className="w-5 h-5 text-cf-steel flex-shrink-0 mt-0.5" />
            <div className="text-xs font-body">
              <strong className="block font-head font-semibold text-sm text-cf-violet-900">No Pending Inquiries</strong>
              <p className="mt-1 text-cf-text-2">
                Your locker is up to date and your insurance claim is in good standing.
              </p>
            </div>
          </div>
        )}
      </Card>

      {/* Deposit Document */}
      <Card className="p-6">
        <h2 className="text-sm font-head font-bold text-cf-violet-900 mb-1 flex items-center gap-2">
          <Upload className="w-4 h-4 text-cf-violet-600" />
          <span>Add a Document to Your Locker</span>
        </h2>
        <p className="text-xs font-body text-cf-text-2 mb-4">
          Safely deposit lab tests, discharge cards, or medical bills. They are encrypted and ready when needed.
        </p>

        {uploadMessage && (
          <div className="mb-4 p-3 rounded-cf-sm bg-cf-info-bg border border-cf-plum/40 text-cf-violet-900 text-xs font-body flex items-center gap-2">
            <Check className="w-4 h-4 text-cf-success" />
            <span>{uploadMessage}</span>
          </div>
        )}

        <form onSubmit={handleUpload} className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
          <input
            type="file"
            required
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
            className="text-xs file:mr-3 file:py-2 file:px-3 file:rounded-cf-sm file:border-0 file:text-xs file:font-head file:font-semibold file:bg-cf-lavender file:text-cf-violet-900 hover:file:bg-cf-plum/40 cursor-pointer"
          />

          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={!uploadFile || uploading}
            loading={uploading}
          >
            <span>Deposit Document</span>
          </Button>
        </form>
      </Card>

      {/* My Vault Records */}
      <Card className="overflow-hidden">
        <div className="p-4 bg-cf-bg-2 border-b border-cf-border flex items-center justify-between">
          <h2 className="text-xs font-head font-bold uppercase tracking-wider text-cf-text-2">
            My Vaulted Records ({documents?.length || 0})
          </h2>
          <span className="text-[11px] font-body text-cf-muted flex items-center gap-1">
            <Lock className="w-3 h-3" />
            <span>Fernet-256 AES Encrypted</span>
          </span>
        </div>

        {(!documents || documents.length === 0) ? (
          <div className="p-8 text-center text-cf-muted text-xs font-head">
            No records deposited in your locker yet.
          </div>
        ) : (
          <div className="divide-y divide-cf-border-2">
            {documents.map(doc => (
              <div key={doc.id} className="p-4 flex items-center justify-between hover:bg-cf-bg transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-cf-sm bg-cf-lavender text-cf-violet-700 flex items-center justify-center">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="font-head font-semibold text-sm text-cf-text block">{doc.filename}</span>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="px-2 py-0.5 rounded-cf-xs text-[10px] font-head font-semibold bg-cf-bg-2 text-cf-steel border border-cf-border capitalize">
                        {doc.doc_type || 'General Record'}
                      </span>
                      <span className="text-[11px] font-body text-cf-muted">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleView(doc.id)}
                >
                  <ExternalLink className="w-3.5 h-3.5 mr-1 text-cf-steel" />
                  <span>View</span>
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
