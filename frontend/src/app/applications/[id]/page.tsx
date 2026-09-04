'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Header } from '@/components/Header';
import {
  ArrowLeft,
  Briefcase,
  Building,
  MapPin,
  CheckCircle2,
  XCircle,
  Clock,
  Calendar,
  Award,
  AlertTriangle,
  History,
  FileText,
  ExternalLink,
  ShieldCheck,
  Send,
  RotateCcw,
  Sparkles,
  Info,
  Check,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Application, ApplicationEvent, ApplicationAttempt, ApplicationStatus } from '@/types';

const statusColors: Record<string, string> = {
  APPLIED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  SUBMITTED: 'bg-blue-50 text-blue-700 border-blue-200',
  QUEUED: 'bg-amber-50 text-amber-700 border-amber-200',
  PREPARING: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  VALIDATING: 'bg-purple-50 text-purple-700 border-purple-200',
  SUBMITTING: 'bg-sky-50 text-sky-700 border-sky-200',
  INTERVIEW_SCHEDULED: 'bg-emerald-50 text-emerald-800 border-emerald-300 font-bold',
  OFFER_RECEIVED: 'bg-amber-100 text-amber-900 border-amber-400 font-black',
  REJECTED: 'bg-rose-50 text-rose-700 border-rose-200',
  FAILED: 'bg-rose-100 text-rose-800 border-rose-300',
  RETRYING: 'bg-amber-50 text-amber-700 border-amber-200',
  BLOCKED: 'bg-slate-100 text-slate-700 border-slate-300',
  DUPLICATE: 'bg-slate-100 text-slate-600 border-slate-200',
  AUTO_APPLY_UNSUPPORTED: 'bg-orange-50 text-orange-700 border-orange-200',
  MISSING_INFORMATION: 'bg-yellow-50 text-yellow-800 border-yellow-300',
  DRAFT: 'bg-slate-100 text-slate-600 border-slate-200',
};

export default function ApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const applicationId = params.id as string;

  const [application, setApplication] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newStatus, setNewStatus] = useState<string>('');
  const [statusNotes, setStatusNotes] = useState<string>('');
  const [updating, setUpdating] = useState(false);
  const [activeTab, setActiveTab] = useState<'timeline' | 'attempts' | 'answers' | 'overview'>('timeline');

  const loadApplicationDetail = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getApplicationDetails(applicationId);
      setApplication(res);
      setNewStatus(res.status);
    } catch (err: any) {
      console.error('Failed to load application details:', err);
      setError(err.message || 'Failed to load application details.');
    } finally {
      setLoading(false);
    }
  }, [applicationId]);

  useEffect(() => {
    if (applicationId) {
      loadApplicationDetail();
    }
  }, [applicationId, loadApplicationDetail]);

  async function handleUpdateStatus(e: React.FormEvent) {
    e.preventDefault();
    if (!application || !newStatus || newStatus === application.status) return;

    try {
      setUpdating(true);
      await api.updateApplicationStatus(application.id, newStatus, statusNotes);
      await loadApplicationDetail();
      setStatusNotes('');
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    } finally {
      setUpdating(false);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex flex-col h-screen">
        <Header title="Application Details" subtitle="Loading timeline & audit history..." />
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-3 text-slate-500 font-medium">
            <Clock className="w-5 h-5 animate-spin text-sky-600" />
            Loading application record...
          </div>
        </div>
      </div>
    );
  }

  if (error || !application) {
    return (
      <div className="flex-1 flex flex-col h-screen bg-slate-50">
        <Header title="Application Details" subtitle="Record not found" />
        <div className="p-8 max-w-xl mx-auto text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-slate-900">Unable to Load Application</h3>
          <p className="text-sm text-slate-500">{error || 'The requested application record could not be found.'}</p>
          <Link
            href="/applications"
            className="inline-flex items-center gap-2 px-4 py-2 bg-sky-600 text-white rounded-xl text-xs font-bold hover:bg-sky-700"
          >
            <ArrowLeft className="w-4 h-4" /> Return to Applications
          </Link>
        </div>
      </div>
    );
  }

  const job = application.job;
  const statusPillClass = statusColors[application.status] || 'bg-slate-100 text-slate-700 border-slate-200';

  return (
    <div className="flex-1 flex flex-col h-screen overflow-y-auto bg-slate-50">
      <Header
        title="Application Audit Trail"
        subtitle={`Tracked application #${application.id.slice(0, 8)} • ${job?.company_name || 'Company'}`}
      />

      <div className="p-6 max-w-6xl mx-auto w-full space-y-6">
        {/* Back Link & Title Header */}
        <div className="flex items-center justify-between">
          <Link
            href="/applications"
            className="inline-flex items-center gap-2 text-xs font-bold text-slate-600 hover:text-slate-900 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-xs"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Tracker
          </Link>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-black uppercase tracking-wider px-3 py-1 rounded-full border ${statusPillClass}`}>
              {application.status.replace(/_/g, ' ')}
            </span>
            {application.submission_method && (
              <span className="text-xs font-bold bg-slate-200/80 text-slate-700 px-2.5 py-1 rounded-full">
                {application.submission_method}
              </span>
            )}
          </div>
        </div>

        {/* Overview Hero Card */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-xl font-black text-slate-900 tracking-tight">{job?.title}</h1>
              <div className="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-slate-600">
                <span className="flex items-center gap-1 font-semibold text-slate-800">
                  <Building className="w-3.5 h-3.5 text-slate-400" /> {job?.company_name}
                </span>
                {job?.location && (
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" /> {job.location} ({job.remote_type})
                  </span>
                )}
                {job?.employment_type && (
                  <span className="flex items-center gap-1">
                    <Briefcase className="w-3.5 h-3.5 text-slate-400" /> {job.employment_type}
                  </span>
                )}
              </div>
            </div>

            {/* Score Pill & Actions */}
            <div className="flex items-center gap-3 shrink-0">
              {application.match_score !== null && application.match_score !== undefined && (
                <div className="px-4 py-2 bg-sky-50 border border-sky-200 rounded-xl text-center">
                  <span className="text-[10px] uppercase tracking-wider font-bold text-sky-600 block">Match Score</span>
                  <span className="text-lg font-black text-sky-700">{Math.round(application.match_score)}%</span>
                </div>
              )}
              {job?.apply_url && (
                <a
                  href={job.apply_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors shadow-xs"
                >
                  Job Posting <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
          </div>

          {/* Key Application Metadata Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-slate-100 text-xs">
            <div>
              <span className="text-slate-400 block text-[11px]">Applied / Submitted Date</span>
              <span className="font-semibold text-slate-800">
                {application.applied_date ? new Date(application.applied_date).toLocaleDateString() : 'Pending Submission'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Platform Connector</span>
              <span className="font-semibold text-slate-800">
                {application.source || job?.job_source?.name || 'Direct / Generic'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Policy Evaluation</span>
              <span className="font-semibold text-slate-800">
                {application.policy_decision || 'AUTO_APPLY'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Confirmation ID</span>
              <span className="font-mono text-slate-700 font-medium">
                {application.external_application_id || 'N/A'}
              </span>
            </div>
          </div>

          {/* Failure reason if any */}
          {application.failure_reason && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-xs text-rose-800">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Reason: </span>
                <span>{application.failure_reason}</span>
              </div>
            </div>
          )}
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 gap-6 text-xs font-bold">
          <button
            onClick={() => setActiveTab('timeline')}
            className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'timeline'
                ? 'border-sky-600 text-sky-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <History className="w-4 h-4" /> Timeline Audit Events ({application.events?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('attempts')}
            className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'attempts'
                ? 'border-sky-600 text-sky-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Send className="w-4 h-4" /> API Submission Attempts ({application.attempts?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('answers')}
            className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'answers'
                ? 'border-sky-600 text-sky-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <FileText className="w-4 h-4" /> Mapped Form Answers ({application.answers?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('overview')}
            className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'overview'
                ? 'border-sky-600 text-sky-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Info className="w-4 h-4" /> Job Summary & Notes
          </button>
        </div>

        {/* Tab 1: Timeline Events */}
        {activeTab === 'timeline' && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <History className="w-4 h-4 text-sky-600" /> Immutable Event Audit Trail
            </h3>

            {(!application.events || application.events.length === 0) ? (
              <p className="text-xs text-slate-500 py-6 text-center">No lifecycle events recorded yet.</p>
            ) : (
              <div className="relative pl-6 space-y-6 before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                {application.events.map((evt) => (
                  <div key={evt.id} className="relative group">
                    <div className="absolute -left-6 top-0.5 w-4 h-4 rounded-full bg-white border-2 border-sky-600 group-hover:scale-125 transition-transform" />
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-900">{evt.title}</span>
                        <span className="text-[10px] font-mono text-slate-400">
                          {new Date(evt.created_at).toLocaleString()}
                        </span>
                      </div>
                      {evt.description && (
                        <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                          {evt.description}
                        </p>
                      )}
                      {(evt.old_status || evt.new_status) && (
                        <div className="flex items-center gap-2 text-[10px] text-slate-500 font-semibold pt-0.5">
                          {evt.old_status && <span>{evt.old_status}</span>}
                          {evt.old_status && evt.new_status && <span>&rarr;</span>}
                          {evt.new_status && <span className="text-sky-700">{evt.new_status}</span>}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Attempts */}
        {activeTab === 'attempts' && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Send className="w-4 h-4 text-sky-600" /> Platform Submission Attempts
            </h3>

            {(!application.attempts || application.attempts.length === 0) ? (
              <p className="text-xs text-slate-500 py-6 text-center">No API submission attempts recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {application.attempts.map((att) => (
                  <div
                    key={att.id}
                    className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col gap-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-900">Attempt #{att.attempt_number}</span>
                        <span className="text-[10px] font-mono bg-slate-200 text-slate-700 px-2 py-0.5 rounded">
                          HTTP {att.response_code || 200}
                        </span>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        att.status === 'SUBMITTED' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                      }`}>
                        {att.status}
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-500 flex items-center gap-4">
                      <span>Method: {att.submission_method}</span>
                      <span>Started: {new Date(att.started_at).toLocaleTimeString()}</span>
                      {att.completed_at && <span>Completed: {new Date(att.completed_at).toLocaleTimeString()}</span>}
                    </div>

                    {att.external_application_id && (
                      <div className="text-xs text-emerald-800 bg-emerald-50 p-2 rounded-lg border border-emerald-100 font-mono">
                        Confirmation ID: {att.external_application_id}
                      </div>
                    )}

                    {att.error_message && (
                      <div className="text-xs text-rose-800 bg-rose-50 p-2 rounded-lg border border-rose-100">
                        Error ({att.error_code}): {att.error_message}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Answers */}
        {activeTab === 'answers' && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <FileText className="w-4 h-4 text-sky-600" /> ATS Form Fields & Verified Answers
            </h3>
            <p className="text-xs text-slate-500">
              Only verified candidate master profile data is used. Zero artificial data fabrication is permitted.
            </p>

            {(!application.answers || application.answers.length === 0) ? (
              <p className="text-xs text-slate-500 py-6 text-center">No custom ATS question answers mapped.</p>
            ) : (
              <div className="space-y-3">
                {application.answers.map((ans) => (
                  <div key={ans.id} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50">
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
                      <span>{ans.question_text}</span>
                      <span className="text-[10px] font-mono bg-sky-100 text-sky-800 px-2 py-0.5 rounded">
                        {ans.confidence_source}
                      </span>
                    </div>
                    <p className="text-xs font-medium text-slate-900 mt-1.5 bg-white p-2.5 rounded-lg border border-slate-200">
                      {ans.answer_text}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Overview & Manual Update */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Job Description Card */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-3">
              <h3 className="text-sm font-bold text-slate-900">Job Description</h3>
              <p className="text-xs text-slate-600 leading-relaxed max-h-96 overflow-y-auto whitespace-pre-line">
                {job?.description}
              </p>
            </div>

            {/* Manual Status Transition Form */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
              <h3 className="text-sm font-bold text-slate-900">Update Application Status</h3>
              <p className="text-xs text-slate-500">
                Manually record interview progress, offer reception, or withdrawal.
              </p>

              <form onSubmit={handleUpdateStatus} className="space-y-4">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Target Status</label>
                  <select
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value)}
                    className="w-full px-3 py-2 text-xs font-medium rounded-xl border border-slate-200 bg-white"
                  >
                    <option value="DRAFT">DRAFT</option>
                    <option value="SUBMITTED">SUBMITTED</option>
                    <option value="UNDER_REVIEW">UNDER_REVIEW</option>
                    <option value="OA_RECEIVED">OA_RECEIVED</option>
                    <option value="INTERVIEW_SCHEDULED">INTERVIEW_SCHEDULED</option>
                    <option value="OFFER_RECEIVED">OFFER_RECEIVED</option>
                    <option value="REJECTED">REJECTED</option>
                    <option value="WITHDRAWN">WITHDRAWN</option>
                    <option value="ARCHIVED">ARCHIVED</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Status Notes (Optional)</label>
                  <textarea
                    rows={3}
                    placeholder="e.g. Completed round 1 screening call with recruiter..."
                    value={statusNotes}
                    onChange={(e) => setStatusNotes(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500"
                  />
                </div>

                <button
                  type="submit"
                  disabled={updating || newStatus === application.status}
                  className="w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs disabled:opacity-50 transition-colors"
                >
                  {updating ? 'Saving Status...' : 'Apply Status Transition'}
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
