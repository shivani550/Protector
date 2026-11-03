import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  ArrowLeft, FileText, HelpCircle, MessageSquare, ShieldAlert, Upload, 
  CheckCircle2, AlertTriangle, Eye, EyeOff, RotateCw, ExternalLink, 
  Send, RefreshCw, Check, ShieldCheck, Mail, Lock
} from 'lucide-react';
import { api } from '../api';
import { Patient, Document, QueryLetter, OutboundMessage, AuditLog } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Chip } from '../components/ui/Chip';
import { Stepper } from '../components/ui/Stepper';
import { PhoneBubble } from '../components/ui/PhoneBubble';
import { EmptyState } from '../components/ui/EmptyState';

export default function PatientDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<'documents' | 'letters' | 'messages' | 'audit'>('documents');
  const [revealed, setRevealed] = useState(false);
  const [selectedLetterId, setSelectedLetterId] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadKind, setUploadKind] = useState('general');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Current user check for audit tab
  const cachedUserStr = localStorage.getItem('user');
  const currentUser = cachedUserStr ? JSON.parse(cachedUserStr) : null;
  const isAdmin = currentUser?.role === 'admin';

  // 1. Fetch Patient details
  const { data: patient, isLoading: loadingPatient } = useQuery<Patient>({
    queryKey: ['patient', id, revealed],
    queryFn: () => api.getPatient(id!, revealed),
    enabled: !!id,
  });

  // 2. Fetch Locker Documents
  const { data: documents, isLoading: loadingDocs, refetch: refetchDocs } = useQuery<Document[]>({
    queryKey: ['documents', id],
    queryFn: () => api.getPatientDocuments(id!),
    enabled: !!id,
  });

  // 3. Fetch Query Letters
  const { data: letters, isLoading: loadingLetters, refetch: refetchLetters } = useQuery<QueryLetter[]>({
    queryKey: ['letters', id],
    queryFn: () => api.getPatientLetters(id!),
    enabled: !!id,
  });

  // 4. Fetch Outbound Messages
  const { data: messages, isLoading: loadingMessages, refetch: refetchMessages } = useQuery<OutboundMessage[]>({
    queryKey: ['messages', id],
    queryFn: () => api.getPatientMessages(id!),
    enabled: !!id,
  });

  // 5. Fetch Audit Log for this patient (if admin)
  const { data: auditLogs } = useQuery<AuditLog[]>({
    queryKey: ['audit-patient', id],
    queryFn: async () => {
      const all = await api.getAdminAudit();
      return all.filter(l => l.patient_id === id);
    },
    enabled: !!id && isAdmin,
  });

  // Default selected letter
  React.useEffect(() => {
    if (letters && letters.length > 0 && !selectedLetterId) {
      setSelectedLetterId(letters[0].id);
    }
  }, [letters, selectedLetterId]);

  // Fetch full details of the active letter (including extracted points & decisions)
  const { data: letterDetail } = useQuery<QueryLetter>({
    queryKey: ['letter-detail', selectedLetterId],
    queryFn: () => api.getLetterDetail(selectedLetterId!),
    enabled: !!selectedLetterId,
  });

  const activeLetter = letterDetail || letters?.find(l => l.id === selectedLetterId) || letters?.[0];

  // Document upload handler
  const handleUpload = async (fileToUpload?: File) => {
    const file = fileToUpload || uploadFile;
    if (!file || !id) return;
    setUploading(true);
    setUploadError(null);
    try {
      await api.uploadDocument(id, file, uploadKind);
      setUploadFile(null);
      refetchDocs();
      refetchLetters();
      refetchMessages();
      queryClient.invalidateQueries({ queryKey: ['letters', id] });
      queryClient.invalidateQueries({ queryKey: ['messages', id] });
      queryClient.invalidateQueries({ queryKey: ['letter-detail', selectedLetterId] });
      queryClient.invalidateQueries({ queryKey: ['patient', id] });
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  // Preview signed URL
  const handleViewDoc = async (docId: string) => {
    try {
      const res = await api.getDocumentSignedUrl(docId);
      window.open(res.url, '_blank');
    } catch (err: any) {
      alert(`Could not generate preview: ${err.message}`);
    }
  };

  // Reprocess Letter
  const reprocessMutation = useMutation({
    mutationFn: (letterId: string) => api.reprocessLetter(letterId),
    onSuccess: () => {
      refetchLetters();
      refetchMessages();
    },
  });

  if (loadingPatient) {
    return (
      <div className="p-16 text-center text-cf-muted">
        <div className="w-8 h-8 border-2 border-cf-violet-600/30 border-t-cf-violet-600 rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs font-head font-medium">Opening Care.fi Health Vault...</p>
      </div>
    );
  }

  if (!patient) {
    return (
      <Card className="p-12 text-center text-cf-text-2">
        <p className="font-head text-base">Patient record not found.</p>
        <Button
          variant="primary"
          onClick={() => navigate('/patients')}
          className="mt-4"
        >
          Return to Patients
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button & Patient Header Card */}
      <div>
        <button
          onClick={() => navigate('/patients')}
          className="inline-flex items-center gap-1.5 text-xs font-head font-semibold text-cf-text-3 hover:text-cf-violet-900 transition-colors mb-3"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Patients</span>
        </button>

        <Card className="p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              {/* Initials Avatar */}
              <div className="w-14 h-14 rounded-full bg-cf-lavender border border-cf-plum/40 text-cf-violet-900 font-head font-bold text-xl flex items-center justify-center shadow-xs">
                {patient.full_name.slice(0, 2).toUpperCase()}
              </div>
              <div>
                <div className="flex items-center gap-2.5">
                  <h1 className="text-2xl font-head font-bold text-cf-violet-900 tracking-tight">{patient.full_name}</h1>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-cf-bg-2 text-cf-steel border border-cf-border">
                    {patient.patient_code}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-xs font-body text-cf-text-2 mt-1.5">
                  <span className="font-medium text-cf-text">
                    Insurer: <strong className="text-cf-violet-900 font-semibold">{patient.insurer_name}</strong>
                  </span>
                  <span>•</span>
                  <span>
                    Policy: <code className="bg-cf-bg px-1.5 py-0.5 rounded text-cf-violet-900 font-mono">{revealed ? patient.policy_number_full || patient.policy_number_masked : patient.policy_number_masked}</code>
                  </span>
                  {patient.aadhaar_masked && (
                    <>
                      <span>•</span>
                      <span>
                        Aadhaar: <code className="bg-cf-bg px-1.5 py-0.5 rounded text-cf-violet-900 font-mono">{revealed ? patient.aadhaar_full || patient.aadhaar_masked : patient.aadhaar_masked}</code>
                      </span>
                    </>
                  )}
                  <span>•</span>
                  <span className="flex items-center gap-1.5">
                    Channels:
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-head font-semibold ${patient.consent_whatsapp ? 'bg-cf-success-bg text-cf-success' : 'bg-cf-bg text-cf-muted'}`}>
                      WA {patient.consent_whatsapp ? 'Opted' : 'Off'}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-head font-semibold ${patient.consent_email ? 'bg-cf-info-bg text-cf-violet-700' : 'bg-cf-bg text-cf-muted'}`}>
                      Email {patient.consent_email ? 'Opted' : 'Off'}
                    </span>
                  </span>
                </div>
              </div>
            </div>

            {/* PII Reveal Button */}
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setRevealed(!revealed)}
                className={revealed ? 'text-cf-danger border-cf-danger/30' : ''}
              >
                {revealed ? <EyeOff className="w-3.5 h-3.5 mr-1" /> : <Eye className="w-3.5 h-3.5 mr-1" />}
                <span>{revealed ? 'Mask PII' : 'Reveal PII'}</span>
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Processing Stepper Banner */}
      {activeLetter && (
        <Stepper 
          status={activeLetter.status} 
          claimRef={activeLetter.claim_ref} 
          totalMs={activeLetter.total_ms} 
          neededCount={activeLetter.needed_points_count ?? (activeLetter.points?.filter(p => p.decision?.decision === 'needs_new_document').length ?? 0)}
        />
      )}

      {/* Tabs Bar (Underline style: active tab violet-600 with 3px plum underline) */}
      <div className="border-b border-cf-border flex items-center gap-6">
        <button
          onClick={() => setActiveTab('documents')}
          className={`flex items-center gap-2 py-3.5 font-head font-semibold text-sm transition-all border-b-[3px] ${
            activeTab === 'documents'
              ? 'border-cf-plum text-cf-violet-900 font-bold'
              : 'border-transparent text-cf-text-3 hover:text-cf-violet-700'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Locker Documents ({documents?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('letters')}
          className={`flex items-center gap-2 py-3.5 font-head font-semibold text-sm transition-all border-b-[3px] ${
            activeTab === 'letters'
              ? 'border-cf-plum text-cf-violet-900 font-bold'
              : 'border-transparent text-cf-text-3 hover:text-cf-violet-700'
          }`}
        >
          <HelpCircle className="w-4 h-4" />
          <span>Query Letters ({letters?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('messages')}
          className={`flex items-center gap-2 py-3.5 font-head font-semibold text-sm transition-all border-b-[3px] ${
            activeTab === 'messages'
              ? 'border-cf-plum text-cf-violet-900 font-bold'
              : 'border-transparent text-cf-text-3 hover:text-cf-violet-700'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span>Outbound Messages ({messages?.length || 0})</span>
        </button>

        {isAdmin && (
          <button
            onClick={() => setActiveTab('audit')}
            className={`flex items-center gap-2 py-3.5 font-head font-semibold text-sm transition-all border-b-[3px] ${
              activeTab === 'audit'
                ? 'border-cf-plum text-cf-violet-900 font-bold'
                : 'border-transparent text-cf-text-3 hover:text-cf-violet-700'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Audit Trail ({auditLogs?.length || 0})</span>
          </button>
        )}
      </div>

      {/* TAB 1: DOCUMENTS */}
      {activeTab === 'documents' && (
        <div className="space-y-6">
          {/* Drag & Drop Zone with Dashed Plum Border and Lavender Fill on Drag-Over */}
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              if (e.dataTransfer.files?.[0]) {
                handleUpload(e.dataTransfer.files[0]);
              }
            }}
            className={`p-6 rounded-cf-lg border-2 border-dashed transition-all duration-200 text-center ${
              isDragging 
                ? 'border-cf-plum bg-cf-lavender shadow-md' 
                : 'border-cf-plum/60 bg-cf-surface hover:bg-cf-bg-2'
            }`}
          >
            <div className="max-w-md mx-auto">
              <div className="w-12 h-12 rounded-cf-md bg-cf-info-bg text-cf-violet-700 flex items-center justify-center mx-auto mb-3">
                <Upload className="w-6 h-6" />
              </div>
              <h3 className="font-head font-bold text-sm text-cf-violet-900 mb-1">
                Deposit Document into Care.fi Locker
              </h3>
              <p className="font-body text-xs text-cf-text-2 mb-4">
                Drag and drop medical records or choose a file from your computer (PDF, PNG, JPG accepted)
              </p>

              {uploadError && (
                <div className="mb-3 p-3 rounded-cf-sm bg-cf-danger-bg text-cf-danger text-xs flex items-center justify-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  <span>{uploadError}</span>
                </div>
              )}

              <form 
                onSubmit={(e) => { e.preventDefault(); handleUpload(); }} 
                className="flex flex-col sm:flex-row gap-3 items-center justify-center"
              >
                <input
                  type="file"
                  id="doc-upload-input"
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="text-xs file:mr-3 file:py-2 file:px-3 file:rounded-cf-sm file:border-0 file:text-xs file:font-head file:font-semibold file:bg-cf-lavender file:text-cf-violet-900 hover:file:bg-cf-plum/40 cursor-pointer"
                />

                <select
                  value={uploadKind}
                  onChange={(e) => setUploadKind(e.target.value)}
                  className="cf-input px-3 py-2 text-xs font-head font-medium bg-cf-surface text-cf-text-2 border border-cf-border rounded-cf-sm"
                >
                  <option value="query_letter">⚡ Insurer Query Letter (Auto-Resolve)</option>
                  <option value="general">Locker Document (General)</option>
                  <option value="query_response">Patient Query Response Document</option>
                  <option value="identity">Identity / KYC Document</option>
                </select>

                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={!uploadFile || uploading}
                  loading={uploading}
                >
                  <span>Deposit</span>
                </Button>
              </form>
            </div>
          </div>

          {/* Vaulted Documents Table */}
          <Card className="overflow-hidden">
            <div className="p-4 bg-cf-bg-2 border-b border-cf-border flex items-center justify-between">
              <h2 className="text-xs font-head font-bold uppercase tracking-wider text-cf-text-2">
                Vaulted Documents ({documents?.length || 0})
              </h2>
              <span className="text-[11px] font-body text-cf-muted flex items-center gap-1">
                <Lock className="w-3 h-3" />
                <span>Fernet AES-256 Storage at Rest</span>
              </span>
            </div>

            {loadingDocs ? (
              <div className="p-8 text-center text-cf-muted text-xs">Loading documents...</div>
            ) : !documents || documents.length === 0 ? (
              <EmptyState 
                title="No documents vaulted yet"
                description="Upload discharge summary, bills, or diagnostic reports using the deposit box above."
              />
            ) : (
              <div className="divide-y divide-cf-border-2">
                {documents.map(doc => {
                  const meta = doc.meta || {};
                  return (
                    <div key={doc.id} className="p-4 hover:bg-cf-bg transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-cf-sm bg-cf-lavender text-cf-violet-700 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <FileText className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-head font-semibold text-cf-text text-sm">{doc.filename}</span>
                            <span className="text-[11px] font-mono text-cf-muted">({Math.round(doc.size / 1024)} KB)</span>
                            {doc.is_superseded && (
                              <span className="px-1.5 py-0.5 rounded-cf-xs text-[10px] bg-cf-warn-bg text-cf-warn font-head font-medium">Superseded</span>
                            )}
                          </div>

                          {/* Classification & Metadata Badges */}
                          <div className="flex flex-wrap items-center gap-2 mt-1.5">
                            <span className="px-2.5 py-0.5 rounded-cf-sm text-xs font-head font-semibold bg-cf-info-bg text-cf-violet-700 border border-cf-plum/30">
                              {doc.doc_type || 'unclassified'}
                            </span>

                            {doc.doc_type_confidence && (
                              <span className="text-[11px] font-body text-cf-muted">
                                Conf: {Math.round(doc.doc_type_confidence * 100)}%
                              </span>
                            )}

                            {doc.legibility_score !== undefined && (
                              <span className={`px-2 py-0.5 rounded-cf-xs text-[11px] font-body font-medium ${
                                doc.legibility_score >= 0.8 ? 'bg-cf-success-bg text-cf-success' : 'bg-cf-danger-bg text-cf-danger'
                              }`}>
                                Legibility: {Math.round(doc.legibility_score * 100)}%
                              </span>
                            )}

                            {/* If this is an insurer query letter, highlight if action is needed or all covered */}
                            {(() => {
                              const matchedLetter = letters?.find(l => l.document_id === doc.id);
                              if (!matchedLetter && doc.doc_kind !== 'query_letter' && doc.doc_type !== 'insurer_query_letter') return null;
                              const needed = matchedLetter?.needed_points_count ?? (matchedLetter?.points?.filter(p => p.decision?.decision === 'needs_new_document').length ?? 0);
                              const covered = matchedLetter?.covered_points_count ?? (matchedLetter?.points?.filter(p => p.decision?.decision === 'covered').length ?? 0);
                              if (needed > 0) {
                                return (
                                  <span 
                                    onClick={() => { setActiveTab('letters'); if (matchedLetter) setSelectedLetterId(matchedLetter.id); }}
                                    className="px-2.5 py-0.5 rounded-cf-xs text-[11px] font-head font-bold bg-cf-warn-bg text-cf-warn border border-cf-warn/30 flex items-center gap-1 cursor-pointer hover:bg-cf-warn-bg/80 transition-colors"
                                  >
                                    <AlertTriangle className="w-3 h-3 text-cf-warn" />
                                    <span>Action Needed · {needed} Document{needed > 1 ? 's' : ''} Missing from Locker</span>
                                  </span>
                                );
                              }
                              if (covered > 0) {
                                return (
                                  <span 
                                    onClick={() => { setActiveTab('letters'); if (matchedLetter) setSelectedLetterId(matchedLetter.id); }}
                                    className="px-2.5 py-0.5 rounded-cf-xs text-[11px] font-head font-bold bg-cf-success-bg text-cf-success border border-cf-success/30 flex items-center gap-1 cursor-pointer hover:bg-cf-success-bg/80 transition-colors"
                                  >
                                    <CheckCircle2 className="w-3 h-3 text-cf-success" />
                                    <span>All Query Points Covered by Locker</span>
                                  </span>
                                );
                              }
                              return null;
                            })()}

                            {meta.name_matches_patient !== undefined && (
                              <span className={`px-2 py-0.5 rounded-cf-xs text-[11px] font-body font-medium ${
                                meta.name_matches_patient ? 'bg-cf-success-bg text-cf-success' : 'bg-cf-danger-bg text-cf-danger'
                              }`}>
                                Name Match: {meta.name_matches_patient ? 'Yes' : 'No'}
                              </span>
                            )}

                            {meta.expiry_date && (
                              <span className="text-[11px] font-body text-cf-muted">
                                Expires: {meta.expiry_date}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleViewDoc(doc.id)}
                      >
                        <ExternalLink className="w-3.5 h-3.5 mr-1 text-cf-steel" />
                        <span>View Document</span>
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* TAB 2: QUERY LETTERS & SPLIT PANE */}
      {activeTab === 'letters' && (
        <div className="space-y-6">
          {(!letters || letters.length === 0) ? (
            <Card className="p-12 text-center text-cf-muted">
              <CheckCircle2 className="w-10 h-10 text-cf-success mx-auto mb-3" />
              <h3 className="text-base font-head font-bold text-cf-violet-900">No Query Letters on Record</h3>
              <p className="text-xs font-body text-cf-text-2 mt-1">
                There are no open or past query deficiency letters for this patient claim.
              </p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Letter Selector & Diagnostics */}
              <div className="lg:col-span-5 space-y-4">
                <Card className="p-4">
                  <h3 className="text-xs font-head font-bold uppercase tracking-wider text-cf-text-2 mb-3">
                    Query Deficiency Letters ({letters.length})
                  </h3>

                  <div className="space-y-2">
                    {letters.map(letter => {
                      const isSelected = letter.id === activeLetter?.id;
                      return (
                        <div
                          key={letter.id}
                          onClick={() => setSelectedLetterId(letter.id)}
                          className={`p-3.5 rounded-cf-md border cursor-pointer transition-all ${
                            isSelected
                              ? 'bg-cf-info-bg border-cf-violet-600 ring-2 ring-cf-plum/20'
                              : 'bg-cf-surface border-cf-border hover:border-cf-thistle'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="font-head font-semibold text-xs text-cf-text">
                              {letter.insurer_name || 'Insurer Letter'}
                            </span>
                            {(() => {
                              const needed = letter.needed_points_count ?? (letter.points?.filter(p => p.decision?.decision === 'needs_new_document').length ?? 0);
                              const covered = letter.covered_points_count ?? (letter.points?.filter(p => p.decision?.decision === 'covered').length ?? 0);
                              const isNeedsDoc = needed > 0;
                              const isCovered = !isNeedsDoc && covered > 0;
                              const statusLabel = isNeedsDoc ? 'Needs Document' : isCovered ? 'Covered' : letter.status;
                              const statusVariant = isNeedsDoc ? 'needs_document' : isCovered ? 'covered' : letter.status === 'failed' ? 'failed' : 'reply_needed';
                              return (
                                <Chip 
                                  label={statusLabel} 
                                  variant={statusVariant as any}
                                  size="sm"
                                />
                              );
                            })()}
                          </div>

                          <div className="flex items-center justify-between text-[11px] font-body text-cf-text-2">
                            <span>Claim: {letter.claim_ref || 'N/A'}</span>
                            <span>{new Date(letter.received_at).toLocaleDateString()}</span>
                          </div>

                          <div className="mt-2 pt-2 border-t border-cf-border flex items-center justify-between text-[11px] font-head">
                            <span className="text-cf-violet-700 font-medium">
                              {letter.points_count || letter.points?.length || 0} Discrete Points
                            </span>
                            {letter.total_ms && (
                              <span className="text-cf-success font-semibold font-mono">
                                {letter.total_ms}ms runtime
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>

                {/* Letter Actions & Diagnostics */}
                {activeLetter && (
                  <Card className="p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-head font-bold uppercase tracking-wider text-cf-text-2">
                        Pipeline Diagnostic
                      </h4>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={reprocessMutation.isPending}
                        onClick={() => reprocessMutation.mutate(activeLetter.id)}
                      >
                        <RotateCw className={`w-3.5 h-3.5 mr-1 ${reprocessMutation.isPending ? 'animate-spin' : ''}`} />
                        <span>Reprocess</span>
                      </Button>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-2.5 rounded-cf-sm bg-cf-bg border border-cf-border">
                        <span className="text-[10px] font-head text-cf-muted block uppercase font-bold">Execution Run</span>
                        <span className="font-head font-semibold text-cf-text">Run #{activeLetter.run_no}</span>
                      </div>
                      <div className="p-2.5 rounded-cf-sm bg-cf-bg border border-cf-border">
                        <span className="text-[10px] font-head text-cf-muted block uppercase font-bold">Resolution Speed</span>
                        <span className="font-head font-semibold text-cf-success">{activeLetter.total_ms ? `${activeLetter.total_ms} ms` : 'In flight'}</span>
                      </div>
                    </div>

                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleViewDoc(activeLetter.document_id)}
                      className="w-full"
                    >
                      <ExternalLink className="w-3.5 h-3.5 mr-1 text-cf-steel" />
                      <span>View Original Insurer PDF</span>
                    </Button>
                  </Card>
                )}
              </div>

              {/* Right Column: Discrete Extracted Points & Guardrail Decisions */}
              <div className="lg:col-span-7 space-y-4">
                <Card className="p-5">
                  {/* Summary Chip Trio */}
                  {activeLetter && (
                    <div className="flex flex-wrap items-center gap-2 pb-3 mb-4 border-b border-cf-border">
                      <Chip 
                        label={`${activeLetter.points_count || activeLetter.points?.length || 0} Total Points`} 
                        variant="neutral" 
                        size="sm"
                      />
                      <Chip 
                        label={`${activeLetter.covered_points_count ?? (activeLetter.points?.filter(p => p.decision?.decision === 'covered').length ?? 0)} Covered by Locker`} 
                        variant="covered" 
                        size="sm"
                      />
                      <Chip 
                        label={`${activeLetter.needed_points_count ?? (activeLetter.points?.filter(p => p.decision?.decision === 'needs_new_document').length ?? 0)} Need Documents`} 
                        variant="needs_document" 
                        size="sm"
                      />
                    </div>
                  )}

                  {(!activeLetter?.points || activeLetter.points.length === 0) ? (
                    <div className="p-8 text-center text-cf-muted text-xs font-head">
                      No points parsed or extraction in progress.
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {activeLetter.points.map((pt) => {
                        const decision = pt.decision;
                        const isCovered = decision?.decision === 'covered';
                        const isNeedsDoc = decision?.decision === 'needs_new_document';

                        return (
                          <div 
                            key={pt.id} 
                            className={`p-4 rounded-cf-md border transition-all ${
                              isCovered 
                                ? 'bg-cf-success-bg/40 border-cf-success/30' 
                                : isNeedsDoc 
                                ? 'bg-cf-warn-bg/40 border-cf-warn/30' 
                                : 'bg-cf-bg border-cf-border'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-3 mb-2">
                              <span className="px-2 py-0.5 rounded-cf-xs text-[10px] font-head font-bold uppercase tracking-wider bg-cf-thistle/50 text-cf-violet-900">
                                Point #{pt.ordinal}
                              </span>

                              {isCovered && (
                                <Chip label="Covered by Locker" variant="covered" size="sm" />
                              )}

                              {isNeedsDoc && (
                                <Chip label="Needs New Document" variant="needs_document" size="sm" />
                              )}
                            </div>

                            {/* Verbatim quote */}
                            <div className="mb-2">
                              <span className="text-[10px] font-head font-semibold uppercase text-cf-muted block mb-0.5">
                                Verbatim Insurer Requirement:
                              </span>
                              <p className="text-xs font-body font-medium text-cf-text bg-cf-surface p-2.5 rounded-cf-sm border border-cf-border italic">
                                "{pt.verbatim_text}"
                              </p>
                            </div>

                            {/* Normalized Ask */}
                            <div className="text-xs font-body text-cf-text-2 mb-2">
                              <span className="font-head font-semibold text-cf-violet-900">Normalized Ask: </span>
                              {pt.normalized_ask}
                            </div>

                            {/* Decision details & check-circle bullet for covered */}
                            {decision && (
                              <div className="pt-2 border-t border-cf-border/60 mt-2 text-xs space-y-1.5 font-body">
                                {isCovered && decision.covering_document_ids && (
                                  <div className="flex items-center gap-1.5 text-cf-success font-head font-medium">
                                    <CheckCircle2 className="w-4 h-4 text-cf-success" />
                                    <span>
                                      Kept from asking: already verified in locker ({decision.covering_document_ids.length} doc match)
                                    </span>
                                  </div>
                                )}

                                {isNeedsDoc && decision.needed_doc_types && (
                                  <div className="flex flex-wrap items-center gap-1.5">
                                    <span className="text-cf-warn font-head font-semibold text-[11px]">Requested from patient:</span>
                                    {decision.needed_doc_types.map(t => (
                                      <span key={t} className="px-2 py-0.5 rounded-cf-xs bg-cf-warn-bg text-cf-warn font-mono text-[10px] font-semibold border border-cf-warn/20">
                                        {t}
                                      </span>
                                    ))}
                                  </div>
                                )}

                                {decision.reason_patient && (
                                  <div className="text-cf-text-2 text-[11px]">
                                    <span className="font-head font-medium text-cf-violet-900">Patient Note: </span>
                                    {decision.reason_patient}
                                  </div>
                                )}

                                {decision.guardrail_flags && decision.guardrail_flags.length > 0 && (
                                  <div className="flex items-center gap-1 text-[11px] text-cf-danger font-medium pt-1">
                                    <ShieldAlert className="w-3.5 h-3.5" />
                                    <span>Guardrail Flags: {decision.guardrail_flags.join(', ')}</span>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </Card>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: OUTBOUND MESSAGES WITH PHONE BUBBLE */}
      {activeTab === 'messages' && (
        <div className="space-y-4">
          <Card className="p-5">
            <h3 className="text-base font-head font-bold text-cf-violet-900">Autonomous Outbound Dispatch</h3>
            <p className="text-xs font-body text-cf-text-2 mt-0.5">
              Zero human action required • Dual-channel dispatch with idempotency protection
            </p>
          </Card>

          {(!messages || messages.length === 0) ? (
            <Card className="p-8 text-center text-cf-muted text-xs font-head">
              No outbound messages dispatched for this patient.
            </Card>
          ) : (
            <div className="space-y-3">
              {messages.map(msg => (
                <PhoneBubble key={msg.id} message={msg} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: AUDIT TRAIL (Admin Only) */}
      {activeTab === 'audit' && isAdmin && (
        <Card className="overflow-hidden">
          <div className="p-4 bg-cf-bg-2 border-b border-cf-border">
            <h3 className="text-xs font-head font-bold uppercase tracking-wider text-cf-text-2">
              Immutable Access & Mutation Journal ({auditLogs?.length || 0})
            </h3>
          </div>

          {(!auditLogs || auditLogs.length === 0) ? (
            <div className="p-8 text-center text-cf-muted text-xs font-head">No audit events recorded for this patient.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-body border-collapse">
                <thead>
                  <tr className="border-b border-cf-border bg-cf-bg text-cf-text-2 uppercase tracking-wider text-[10px] font-head">
                    <th className="py-2.5 px-4">Timestamp</th>
                    <th className="py-2.5 px-4">Actor</th>
                    <th className="py-2.5 px-4">Role</th>
                    <th className="py-2.5 px-4">Action</th>
                    <th className="py-2.5 px-4">Result</th>
                    <th className="py-2.5 px-4">IP Address</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cf-border-2">
                  {auditLogs.map(log => (
                    <tr key={log.id} className="hover:bg-cf-bg">
                      <td className="py-2.5 px-4 font-mono text-cf-muted">{new Date(log.ts).toLocaleString()}</td>
                      <td className="py-2.5 px-4 font-head font-medium text-cf-text">{log.actor_user_id || 'system'}</td>
                      <td className="py-2.5 px-4 text-cf-text-2">{log.actor_role || 'system'}</td>
                      <td className="py-2.5 px-4 font-mono text-cf-violet-700">{log.action}</td>
                      <td className="py-2.5 px-4">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-head font-semibold ${
                          log.result === 'allowed' || log.result === 'success'
                            ? 'bg-cf-success-bg text-cf-success'
                            : 'bg-cf-danger-bg text-cf-danger'
                        }`}>
                          {log.result}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 font-mono text-cf-muted">{log.ip || '127.0.0.1'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
