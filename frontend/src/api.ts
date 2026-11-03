import {
  User, Patient, Document, QueryLetter, OutboundMessage, AdminStats, PreflightStatus, Job, AuditLog
} from './types';

const API_BASE = '/api';

async function parseErrorResponse(res: Response, fallback: string): Promise<string> {
  try {
    const text = await res.text();
    try {
      const data = JSON.parse(text);
      return data.detail || data.message || (typeof data === 'string' ? data : JSON.stringify(data));
    } catch {
      return text || fallback;
    }
  } catch {
    return fallback;
  }
}

async function fetchJson<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
  });

  if (res.status === 401 && !url.includes('/auth/login')) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const errDetail = await parseErrorResponse(res, `Request failed with status ${res.status}`);
    throw new Error(errDetail);
  }

  return res.json();
}

export const api = {
  // Auth
  login: async (email: string, password: string): Promise<{ access_token: string; role: string; user_id: string; patient_id?: string }> => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const errMsg = await parseErrorResponse(res, 'Login failed');
      throw new Error(errMsg);
    }
    const data = await res.json();
    localStorage.setItem('token', data.access_token);
    return data;
  },

  logout: async () => {
    try {
      await fetchJson('/auth/logout', { method: 'POST' });
    } finally {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
  },

  getMe: () => fetchJson<User>('/auth/me'),

  // Patients
  getPatients: () => fetchJson<Patient[]>('/patients'),
  getPatient: (id: string, reveal = false) => fetchJson<Patient>(`/patients/${id}${reveal ? '?reveal=true' : ''}`),

  // Documents
  getPatientDocuments: (patientId: string) => fetchJson<Document[]>(`/patients/${patientId}/documents`),
  uploadDocument: async (patientId: string, file: File, docKind = 'general', claimRef?: string) => {
    const token = localStorage.getItem('token');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_kind', docKind);
    if (claimRef) formData.append('claim_ref', claimRef);

    const res = await fetch(`${API_BASE}/patients/${patientId}/documents`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const errMsg = await parseErrorResponse(res, 'Upload failed');
      throw new Error(errMsg);
    }
    return res.json();
  },
  getDocumentSignedUrl: (docId: string) => fetchJson<{ url: string; expires_at: string }>(`/documents/${docId}/signed-url`),

  // Query Letters
  getPatientLetters: (patientId: string) => fetchJson<QueryLetter[]>(`/patients/${patientId}/letters`),
  getLetterDetail: (letterId: string) => fetchJson<QueryLetter>(`/letters/${letterId}`),
  reprocessLetter: (letterId: string) => fetchJson<{ message: string; run_no: number }>(`/letters/${letterId}/reprocess`, { method: 'POST' }),

  // Messages
  getPatientMessages: (patientId: string) => fetchJson<OutboundMessage[]>(`/patients/${patientId}/messages`),
  resendMessage: (messageId: string) => fetchJson<{ message: string; status: string }>(`/messages/${messageId}/resend`, { method: 'POST' }),

  // Admin
  getAdminStats: () => fetchJson<AdminStats>('/admin/stats'),
  getAdminJobs: () => fetchJson<Job[]>('/admin/jobs'),
  retryAdminJob: (jobId: string) => fetchJson<{ message: string }>(`/admin/jobs/${jobId}/retry`, { method: 'POST' }),
  getAdminAudit: () => fetchJson<AuditLog[]>('/admin/audit'),
  getAdminPreflight: () => fetchJson<PreflightStatus>('/admin/preflight'),

  // Magic Link Upload
  getMagicUploadInfo: (token: string) => fetchJson<{ patient_first_name: string; insurer_name: string; requested_documents: any[] }>(`/upload/${token}`),
  submitMagicUpload: async (token: string, file: File, docType = 'other') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', docType);
    const res = await fetch(`${API_BASE}/upload/${token}`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const errMsg = await parseErrorResponse(res, 'Upload failed');
      throw new Error(errMsg);
    }
    return res.json();
  },
};
