'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { Header } from '@/components/Header';
import {
  Briefcase,
  Clock,
  CheckCircle2,
  Calendar,
  Award,
  XCircle,
  Building,
  MapPin,
  ChevronRight,
  History,
  FileText,
  Search,
  Filter,
  Zap,
  ShieldCheck,
  AlertTriangle,
  RotateCcw,
  ExternalLink,
  Layers,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Application, ApplicationStatus, ApplicationStatistics } from '@/types';

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [stats, setStats] = useState<ApplicationStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterTab, setFilterTab] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [appsRes, statsRes] = await Promise.all([
        api.getApplications(statusFilter || undefined),
        api.getApplicationStatistics(),
      ]);
      setApplications(appsRes);
      setStats(statsRes);
    } catch (err) {
      console.error('Failed to load applications:', err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleStatusChange(appId: string, newStatus: string) {
    try {
      await api.updateApplicationStatus(appId, newStatus);
      await loadData();
    } catch (err: any) {
      alert(`Error updating status: ${err.message}`);
    }
  }

  const filteredApps = applications.filter((app) => {
    const titleMatch = (app.job?.title || '').toLowerCase().includes(searchQuery.toLowerCase());
    const compMatch = (app.job?.company_name || '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSearch = titleMatch || compMatch;

    if (!matchesSearch) return false;

    if (filterTab === 'ALL') return true;
    if (filterTab === 'APPLIED') return ['APPLIED', 'SUBMITTED'].includes(app.status);
    if (filterTab === 'QUEUED') return ['QUEUED', 'PREPARING', 'VALIDATING', 'SUBMITTING', 'RETRYING'].includes(app.status);
    if (filterTab === 'INTERVIEWS') return ['INTERVIEW_SCHEDULED', 'OFFER_RECEIVED'].includes(app.status);
    if (filterTab === 'SKIPPED') return ['POLICY_PENDING', 'BLOCKED', 'DUPLICATE'].includes(app.status);
    if (filterTab === 'UNSUPPORTED') return ['AUTO_APPLY_UNSUPPORTED', 'MISSING_INFORMATION', 'FAILED'].includes(app.status);

    return true;
  });

  return (
    <div className="flex-1 flex flex-col h-screen overflow-y-auto bg-slate-50">
      <Header
        title="Applications Tracker"
        subtitle="End-to-end lifecycle tracking with automated state machines & event auditing"
      />

      <div className="p-6 max-w-7xl mx-auto w-full space-y-6">
        {/* Top Summary Banner */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Total Applications</span>
            <span className="text-2xl font-black text-slate-900 mt-1 block">{stats?.total_applications || applications.length}</span>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
            <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider block">Applied / Submitted</span>
            <span className="text-2xl font-black text-emerald-700 mt-1 block">{stats?.applied_count || 0}</span>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
            <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-wider block">Queued / Running</span>
            <span className="text-2xl font-black text-indigo-700 mt-1 block">{stats?.queued_count || 0}</span>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
            <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider block">Interviews Scheduled</span>
            <span className="text-2xl font-black text-amber-700 mt-1 block">{stats?.interview_count || 0}</span>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
            <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider block">Offers Received</span>
            <span className="text-2xl font-black text-emerald-700 mt-1 block">{stats?.offer_count || 0}</span>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Auto-Apply Engine</span>
            <Link
              href="/auto-apply"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-sky-600 hover:text-sky-800"
            >
              <Zap className="w-3.5 h-3.5" /> Policy & Queue &rarr;
            </Link>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Filter Tabs */}
          <div className="flex flex-wrap gap-1.5 text-xs font-bold">
            {[
              { key: 'ALL', label: 'All Applications' },
              { key: 'APPLIED', label: 'Applied' },
              { key: 'QUEUED', label: 'Queued / Processing' },
              { key: 'INTERVIEWS', label: 'Interviews & Offers' },
              { key: 'SKIPPED', label: 'Policy Skipped' },
              { key: 'UNSUPPORTED', label: 'Action Required' },
            ].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setFilterTab(key)}
                className={`px-3 py-1.5 rounded-xl transition-all ${
                  filterTab === key
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div className="relative min-w-[240px]">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by role or company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>
        </div>

        {/* Applications List View */}
        <div className="space-y-3">
          {loading ? (
            <div className="p-12 text-center text-slate-400 text-xs font-medium">Loading applications...</div>
          ) : filteredApps.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-2xl border border-dashed border-slate-200">
              <Briefcase className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <h3 className="text-sm font-bold text-slate-700">No applications match this filter</h3>
              <p className="text-xs text-slate-500 mt-1">
                Explore recommended jobs or enable Auto-Apply to automatically apply to matching roles.
              </p>
              <div className="mt-4 flex items-center justify-center gap-3">
                <Link
                  href="/recommended"
                  className="px-4 py-2 bg-sky-600 text-white rounded-xl text-xs font-bold hover:bg-sky-700"
                >
                  View Recommendations
                </Link>
                <Link
                  href="/auto-apply"
                  className="px-4 py-2 bg-slate-100 text-slate-700 rounded-xl text-xs font-bold hover:bg-slate-200"
                >
                  Auto-Apply Settings
                </Link>
              </div>
            </div>
          ) : (
            filteredApps.map((app) => (
              <div
                key={app.id}
                className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs hover:border-sky-300 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-bold text-slate-900">{app.job?.title || 'Job Posting'}</span>
                    <span className="text-xs font-semibold text-slate-600">• {app.job?.company_name}</span>
                    {app.match_score !== null && app.match_score !== undefined && (
                      <span className="text-[10px] font-black bg-sky-50 text-sky-700 border border-sky-200 px-2 py-0.5 rounded-md">
                        {Math.round(app.match_score)}% MATCH
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <Building className="w-3.5 h-3.5 text-slate-400" /> {app.source || app.job?.job_source?.name || 'Platform'}
                    </span>
                    {app.job?.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-slate-400" /> {app.job.location} ({app.job.remote_type})
                      </span>
                    )}
                    <span>Method: {app.submission_method}</span>
                    {app.applied_date && (
                      <span>Applied: {new Date(app.applied_date).toLocaleDateString()}</span>
                    )}
                  </div>

                  {app.failure_reason && (
                    <div className="text-[11px] text-rose-700 bg-rose-50 p-2 rounded-lg border border-rose-100 mt-1 leading-tight inline-block">
                      {app.failure_reason}
                    </div>
                  )}
                </div>

                {/* Status Badge & Action Buttons */}
                <div className="flex items-center gap-3 shrink-0">
                  <div className="flex flex-col items-end gap-1.5">
                    <span
                      className={`text-[11px] font-black uppercase px-3 py-1 rounded-full border ${
                        app.status === 'APPLIED' || app.status === 'SUBMITTED'
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                          : app.status === 'INTERVIEW_SCHEDULED' || app.status === 'OFFER_RECEIVED'
                          ? 'bg-amber-100 text-amber-900 border-amber-300'
                          : app.status === 'QUEUED' || app.status === 'SUBMITTING'
                          ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                          : app.status === 'BLOCKED' || app.status === 'POLICY_PENDING'
                          ? 'bg-slate-100 text-slate-700 border-slate-200'
                          : 'bg-rose-50 text-rose-700 border-rose-200'
                      }`}
                    >
                      {app.status.replace(/_/g, ' ')}
                    </span>

                    {/* Move status select */}
                    <select
                      value={app.status}
                      onChange={(e) => handleStatusChange(app.id, e.target.value)}
                      className="text-[11px] font-medium bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-slate-600 focus:outline-none"
                    >
                      <option value="DRAFT">Set Draft</option>
                      <option value="SUBMITTED">Set Submitted</option>
                      <option value="UNDER_REVIEW">Set Under Review</option>
                      <option value="OA_RECEIVED">Set OA Received</option>
                      <option value="INTERVIEW_SCHEDULED">Set Interview</option>
                      <option value="OFFER_RECEIVED">Set Offer</option>
                      <option value="REJECTED">Set Rejected</option>
                      <option value="WITHDRAWN">Set Withdrawn</option>
                    </select>
                  </div>

                  {app.status === 'EXTERNAL_APPLICATION_REQUIRED' && (
                    <a
                      href={app.metadata_json?.direct_apply_url || app.job?.apply_url || '#'}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold transition-colors shadow-xs"
                      title="Open external application portal"
                    >
                      <span>Open Application</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}

                  <Link
                    href={`/applications/${app.id}`}
                    className="p-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 hover:text-slate-900 transition-colors"
                    title="View Timeline & Details"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
