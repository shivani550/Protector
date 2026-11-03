import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { 
  Search, Users, FileText, HelpCircle, CheckCircle2, Clock, 
  AlertTriangle, MessageSquare, Mail, ChevronRight
} from 'lucide-react';
import { api } from '../api';
import { Patient } from '../types';
import { Card } from '../components/ui/Card';
import { Chip } from '../components/ui/Chip';

export default function PatientsList() {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'open_queries' | 'has_docs'>('all');
  const [insurerFilter, setInsurerFilter] = useState<string>('all');

  const { data: patients, isLoading, error } = useQuery<Patient[]>({
    queryKey: ['patients'],
    queryFn: api.getPatients,
    refetchInterval: 10000,
  });

  const insurers = Array.from(new Set(patients?.map(p => p.insurer_name) || [])).filter(Boolean);

  const filteredPatients = patients?.filter(p => {
    const matchesSearch = 
      p.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.patient_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.insurer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.policy_number_masked.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = 
      statusFilter === 'all' ? true :
      statusFilter === 'open_queries' ? (p.open_queries_count || 0) > 0 :
      statusFilter === 'has_docs' ? (p.documents_count || 0) > 0 : true;

    const matchesInsurer = 
      insurerFilter === 'all' ? true : p.insurer_name === insurerFilter;

    return matchesSearch && matchesStatus && matchesInsurer;
  }) || [];

  const totalPatients = patients?.length || 0;
  const patientsWithOpenQueries = patients?.filter(p => (p.open_queries_count || 0) > 0).length || 0;
  const totalLockerDocs = patients?.reduce((acc, p) => acc + (p.documents_count || 0), 0) || 0;

  return (
    <div className="space-y-6">
      {/* Hero Header Band */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <span className="text-xs font-head font-semibold uppercase tracking-wider text-cf-steel">
            Care.fi Health Vault Directory
          </span>
          <h1 className="text-2xl sm:text-3xl font-head font-bold text-cf-violet-900 tracking-tight mt-0.5">
            Patients
          </h1>
          <p className="text-xs font-body text-cf-text-2 mt-1">
            DigiLocker-grade document repositories and autonomous insurance query states
          </p>
        </div>
      </div>

      {/* 3 Stat Tiles in Care.fi Style */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-cf-sm bg-cf-lavender text-cf-violet-700 flex items-center justify-center flex-shrink-0">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-head font-semibold uppercase tracking-wider text-cf-muted">
              Total Enrolled
            </span>
            <div className="text-2xl font-head font-bold text-cf-text">{totalPatients}</div>
          </div>
        </Card>

        <Card className="p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-cf-sm bg-cf-warn-bg text-cf-warn flex items-center justify-center flex-shrink-0">
            <HelpCircle className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-head font-semibold uppercase tracking-wider text-cf-muted">
              Active Queries
            </span>
            <div className="text-2xl font-head font-bold text-cf-warn">{patientsWithOpenQueries}</div>
          </div>
        </Card>

        <Card className="p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-cf-sm bg-cf-success-bg text-cf-success flex items-center justify-center flex-shrink-0">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-head font-semibold uppercase tracking-wider text-cf-muted">
              Vaulted Documents
            </span>
            <div className="text-2xl font-head font-bold text-cf-text">{totalLockerDocs}</div>
          </div>
        </Card>
      </div>

      {/* Search & Filters */}
      <Card className="p-4 flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-cf-muted absolute left-3.5 top-3.5 pointer-events-none" />
          <input
            type="text"
            placeholder="Search by patient name, code (PT-XXXX), insurer, policy..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="cf-input w-full pl-10 pr-4 py-2.5 text-xs font-body rounded-cf-md"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={statusFilter}
            onChange={(e: any) => setStatusFilter(e.target.value)}
            className="cf-input px-3 py-2 text-xs font-head font-medium bg-cf-surface text-cf-text-2"
          >
            <option value="all">All Query States</option>
            <option value="open_queries">Active Queries Only</option>
            <option value="has_docs">With Vaulted Docs</option>
          </select>

          <select
            value={insurerFilter}
            onChange={(e) => setInsurerFilter(e.target.value)}
            className="cf-input px-3 py-2 text-xs font-head font-medium bg-cf-surface text-cf-text-2"
          >
            <option value="all">All Insurers</option>
            {insurers.map(ins => (
              <option key={ins} value={ins}>{ins}</option>
            ))}
          </select>
        </div>
      </Card>

      {/* Patients Table */}
      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-cf-muted">
            <div className="w-8 h-8 border-2 border-cf-violet-600/30 border-t-cf-violet-600 rounded-full animate-spin mx-auto mb-3" />
            <p className="text-xs font-head font-medium">Loading patients and locker states...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-cf-danger bg-cf-danger-bg/50">
            <AlertTriangle className="w-6 h-6 mx-auto mb-2" />
            <p className="text-xs font-head font-medium">Failed to load patient records.</p>
          </div>
        ) : filteredPatients.length === 0 ? (
          <div className="p-12 text-center text-cf-text-2">
            <Users className="w-8 h-8 mx-auto text-cf-muted mb-2" />
            <p className="text-sm font-head font-medium text-cf-text">No matching patients found</p>
            <p className="text-xs font-body text-cf-muted mt-1">Try adjusting your search criteria or filters</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs font-body">
              <thead>
                <tr className="border-b border-cf-border bg-cf-bg-2 text-[11px] font-head font-semibold uppercase tracking-wider text-cf-text-2">
                  <th className="py-3.5 px-4">Patient Code & Name</th>
                  <th className="py-3.5 px-4">Insurer & Policy</th>
                  <th className="py-3.5 px-4">Locker Vault</th>
                  <th className="py-3.5 px-4">Query Status</th>
                  <th className="py-3.5 px-4">Channels</th>
                  <th className="py-3.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-cf-border-2">
                {filteredPatients.map(patient => {
                  const hasQueries = (patient.open_queries_count || 0) > 0;
                  return (
                    <tr
                      key={patient.id}
                      onClick={() => navigate(`/patients/${patient.id}`)}
                      className="hover:bg-cf-bg cursor-pointer transition-colors group"
                    >
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-3">
                          {/* Care.fi Lavender Initials Circle */}
                          <div className="w-9 h-9 rounded-full bg-cf-lavender text-cf-violet-900 font-head font-bold text-xs flex items-center justify-center flex-shrink-0 shadow-xs border border-cf-plum/30">
                            {patient.full_name.slice(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-head font-semibold text-cf-text group-hover:text-cf-violet-700 transition-colors">
                              {patient.full_name}
                            </div>
                            <div className="text-[11px] font-mono text-cf-text-3">
                              {patient.patient_code}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-head font-medium text-cf-text">{patient.insurer_name}</div>
                        <div className="text-[11px] font-mono text-cf-text-3">{patient.policy_number_masked}</div>
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-cf-sm text-xs font-head font-medium bg-cf-bg text-cf-text-2 border border-cf-border">
                          <FileText className="w-3.5 h-3.5 text-cf-steel" />
                          <span>{patient.documents_count || 0} docs</span>
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        {hasQueries ? (
                          <Chip 
                            label={`${patient.open_queries_count} Pending Query`} 
                            variant="needs_document" 
                            size="sm"
                          />
                        ) : (
                          <Chip 
                            label="All Clear" 
                            variant="covered" 
                            size="sm"
                          />
                        )}
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <span 
                            title={patient.consent_whatsapp ? 'WhatsApp Opted In' : 'WhatsApp Opted Out'}
                            className={`p-1.5 rounded-cf-xs ${patient.consent_whatsapp ? 'bg-cf-success-bg text-cf-success' : 'bg-cf-bg-2 text-cf-muted'}`}
                          >
                            <MessageSquare className="w-3.5 h-3.5" />
                          </span>
                          <span 
                            title={patient.consent_email ? 'Email Opted In' : 'Email Opted Out'}
                            className={`p-1.5 rounded-cf-xs ${patient.consent_email ? 'bg-cf-info-bg text-cf-violet-700' : 'bg-cf-bg-2 text-cf-muted'}`}
                          >
                            <Mail className="w-3.5 h-3.5" />
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <span className="inline-flex items-center gap-1 text-xs font-head font-semibold text-cf-violet-600 group-hover:text-cf-violet-900 transition-colors">
                          <span>View Locker</span>
                          <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
