'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Header } from '@/components/Header';
import { MatchBreakdownModal } from '@/components/MatchBreakdownModal';
import {
  Search,
  Building,
  MapPin,
  DollarSign,
  Filter,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
  RefreshCw,
  Layers,
  Calendar,
  Briefcase,
  GraduationCap,
  Clock,
  ChevronRight,
  Info,
  X,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Job, JobMatch, NormalizedJob, ConnectorInfo } from '@/types';

const SOURCE_TABS = [
  { id: 'ALL', label: 'All Sources' },
  { id: 'greenhouse', label: 'Greenhouse' },
  { id: 'lever', label: 'Lever' },
  { id: 'authorized_api', label: 'Authorized Feed' },
  { id: 'linkedin', label: 'LinkedIn' },
  { id: 'indeed', label: 'Indeed' },
  { id: 'naukri', label: 'Naukri' },
  { id: 'unstop', label: 'Unstop' },
  { id: 'internshala', label: 'Internshala' },
  { id: 'wellfound', label: 'Wellfound' },
  { id: 'career_pages', label: 'Direct Career Sites' },
];

export default function JobsDiscoveryPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ text: string; type: 'success' | 'info' } | null>(null);

  // Search & Filter state
  const [query, setQuery] = useState('');
  const [locationFilter, setLocationFilter] = useState('');
  const [remoteFilter, setRemoteFilter] = useState('ALL');
  const [expFilter, setExpFilter] = useState('ALL');
  const [empFilter, setEmpFilter] = useState('ALL');
  const [datePostedFilter, setDatePostedFilter] = useState('ALL');
  const [selectedSource, setSelectedSource] = useState('ALL');
  const [minSalary, setMinSalary] = useState('');

  // Modals state
  const [selectedMatch, setSelectedMatch] = useState<JobMatch | null>(null);
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);
  const [inspectedJob, setInspectedJob] = useState<NormalizedJob | null>(null);
  const [loadingInspection, setLoadingInspection] = useState(false);

  const loadJobs = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (query.trim()) params.query = query.trim();
      if (locationFilter.trim()) params.location = locationFilter.trim();
      if (remoteFilter !== 'ALL') params.remote_type = remoteFilter;
      if (expFilter !== 'ALL') params.experience_level = expFilter;
      if (empFilter !== 'ALL') params.employment_type = empFilter;
      if (datePostedFilter !== 'ALL') params.date_posted = datePostedFilter;
      if (selectedSource !== 'ALL') params.source = selectedSource;
      if (minSalary) params.min_salary = minSalary;

      const res = await api.getJobs(params);
      setJobs(res);
    } catch (err) {
      console.error('Failed to load jobs:', err);
    } finally {
      setLoading(false);
    }
  }, [query, locationFilter, remoteFilter, expFilter, empFilter, datePostedFilter, selectedSource, minSalary]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  async function handleSyncDiscovery() {
    try {
      setSyncing(true);
      setStatusMsg({ text: 'Syncing across 10 platform connectors & deduplicating jobs...', type: 'info' });
      const res = await api.triggerJobSync();
      await loadJobs();
      setStatusMsg({
        text: `Discovery complete! Discovered ${res.data.total_discovered} postings across ${res.data.total_connectors_synced} connectors (${res.data.new_jobs_ingested} newly ingested).`,
        type: 'success',
      });
      setTimeout(() => setStatusMsg(null), 5000);
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setSyncing(false);
    }
  }

  async function handleAnalyzeMatch(jobId: string) {
    try {
      setAnalyzingId(jobId);
      const match = await api.getJobMatch(jobId);
      setSelectedMatch(match);
    } catch (err: any) {
      alert(`Error calculating match: ${err.message}`);
    } finally {
      setAnalyzingId(null);
    }
  }

  async function handleInspectJob(jobId: string) {
    try {
      setLoadingInspection(true);
      const detail = await api.getJobById(jobId);
      setInspectedJob(detail);
    } catch (err: any) {
      alert(`Error loading job details: ${err.message}`);
    } finally {
      setLoadingInspection(false);
    }
  }

  const getCapabilityBadge = (capabilityStatus?: string) => {
    switch (capabilityStatus) {
      case 'SUPPORTED_AUTO_APPLY':
      case 'AUTO_APPLY':
        return (
          <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-emerald-600" /> Direct API (Auto-Apply)
          </span>
        );
      case 'SUPPORTED_JOB_DISCOVERY_ONLY':
      case 'JOB_DISCOVERY':
        return (
          <span className="bg-sky-50 text-sky-700 border border-sky-200 text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-sky-600" /> Partner Discovery
          </span>
        );
      case 'EXTERNAL_APPLICATION_REQUIRED':
      case 'EXTERNAL_APPLICATION':
        return (
          <span className="bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
            <AlertCircle className="w-3 h-3 text-amber-600" /> External Portal Apply
          </span>
        );
      default:
        return (
          <span className="bg-slate-100 text-slate-600 text-[10px] font-bold px-2 py-0.5 rounded-full">
            Standard Source
          </span>
        );
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Job Discovery Engine"
        subtitle="Platform-independent job search across 10 authorized adapters with SHA-256 deduplication"
        actionButton={
          <button
            onClick={handleSyncDiscovery}
            disabled={syncing}
            className="flex items-center gap-2 bg-gradient-to-r from-sky-500 to-indigo-600 hover:opacity-95 text-white text-xs font-bold px-4 py-2 rounded-xl shadow-sm transition-opacity"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
            <span>{syncing ? 'Discovering...' : 'Sync & Discover Jobs'}</span>
          </button>
        }
      />

      <div className="p-8 space-y-6 max-w-7xl w-full mx-auto">
        {/* Sync / Status Banner */}
        {statusMsg && (
          <div
            className={`p-4 rounded-xl text-xs font-semibold flex items-center gap-2.5 border animate-in fade-in duration-200 ${
              statusMsg.type === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-sky-50 border-sky-200 text-sky-800'
            }`}
          >
            <Sparkles className="w-4 h-4 text-sky-600 shrink-0" />
            <span>{statusMsg.text}</span>
          </div>
        )}

        {/* 10 Source Filter Tabs */}
        <div className="bg-white p-2 rounded-2xl border border-slate-200 shadow-xs flex items-center gap-1.5 overflow-x-auto no-scrollbar">
          {SOURCE_TABS.map((tab) => {
            const isSelected = selectedSource === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setSelectedSource(tab.id)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors ${
                  isSelected
                    ? 'bg-slate-900 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Multi-Criteria Search & Filter Toolbar */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              loadJobs();
            }}
            className="flex flex-col md:flex-row gap-3 items-center"
          >
            <div className="flex-1 w-full flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs">
              <Search className="w-4 h-4 text-slate-400 shrink-0" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by title, company, skills, or keywords (e.g. Python, Stripe, Distributed Systems)..."
                className="bg-transparent border-none focus:outline-none w-full text-slate-900 placeholder:text-slate-400"
              />
            </div>

            <div className="w-full md:w-64 flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs">
              <MapPin className="w-4 h-4 text-slate-400 shrink-0" />
              <input
                type="text"
                value={locationFilter}
                onChange={(e) => setLocationFilter(e.target.value)}
                placeholder="Location (e.g. Remote, San Francisco)..."
                className="bg-transparent border-none focus:outline-none w-full text-slate-900 placeholder:text-slate-400"
              />
            </div>

            <button
              type="submit"
              className="w-full md:w-auto bg-slate-900 hover:bg-slate-800 text-white px-6 py-2.5 rounded-xl text-xs font-semibold transition-colors shrink-0"
            >
              Search
            </button>
          </form>

          {/* Secondary Filter Dropdowns */}
          <div className="flex flex-wrap items-center gap-3 pt-1 text-xs">
            <div className="flex items-center gap-1.5 font-bold text-slate-500">
              <Filter className="w-3.5 h-3.5" /> Filters:
            </div>

            <select
              value={remoteFilter}
              onChange={(e) => setRemoteFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 font-semibold text-slate-700 focus:outline-none"
            >
              <option value="ALL">All Work Modes</option>
              <option value="REMOTE">100% Remote</option>
              <option value="HYBRID">Hybrid</option>
              <option value="ONSITE">Onsite</option>
            </select>

            <select
              value={expFilter}
              onChange={(e) => setExpFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 font-semibold text-slate-700 focus:outline-none"
            >
              <option value="ALL">All Seniority</option>
              <option value="ENTRY">Entry Level</option>
              <option value="MID_LEVEL">Mid Level</option>
              <option value="SENIOR">Senior</option>
              <option value="LEAD">Staff / Lead</option>
            </select>

            <select
              value={empFilter}
              onChange={(e) => setEmpFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 font-semibold text-slate-700 focus:outline-none"
            >
              <option value="ALL">All Employment Types</option>
              <option value="FULL_TIME">Full Time</option>
              <option value="CONTRACT">Contract</option>
              <option value="INTERNSHIP">Internship</option>
              <option value="PART_TIME">Part Time</option>
            </select>

            <select
              value={datePostedFilter}
              onChange={(e) => setDatePostedFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 font-semibold text-slate-700 focus:outline-none"
            >
              <option value="ALL">Date Posted: Any Time</option>
              <option value="24H">Past 24 Hours</option>
              <option value="WEEK">Past Week</option>
              <option value="MONTH">Past Month</option>
            </select>

            <input
              type="number"
              value={minSalary}
              onChange={(e) => setMinSalary(e.target.value)}
              onBlur={loadJobs}
              placeholder="Min Salary (e.g. 150000)"
              className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 font-semibold text-slate-700 w-36 focus:outline-none"
            />
          </div>
        </div>

        {/* Jobs Feed List */}
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold px-1">
            <span>Found {jobs.length} verified normalized postings</span>
            <span>Non-circumvention & safe application policies active</span>
          </div>

          {loading ? (
            <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center text-xs text-slate-400">
              Searching jobs across active connectors...
            </div>
          ) : jobs.length > 0 ? (
            jobs.map((job) => (
              <div
                key={job.id}
                className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs hover:shadow-md transition-shadow flex flex-col md:flex-row md:items-center justify-between gap-6"
              >
                <div className="space-y-2.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-bold text-slate-900">{job.title}</h3>
                    {getCapabilityBadge(job.job_source?.capability_status)}
                    <span className="text-[10px] font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                      {job.experience_level.replace('_', ' ')}
                    </span>
                    <span className="text-[10px] font-bold bg-slate-100 text-slate-500 px-2 py-0.5 rounded uppercase">
                      {job.job_source?.slug || 'direct'}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
                    <span className="flex items-center gap-1 font-semibold text-slate-800">
                      <Building className="w-3.5 h-3.5" /> {job.company_name}
                    </span>
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5" /> {job.location || 'Remote'}
                    </span>
                    {job.salary_min && (
                      <span className="flex items-center gap-1 text-emerald-600 font-bold">
                        <DollarSign className="w-3.5 h-3.5" /> ${(job.salary_min / 1000).toFixed(0)}k - ${(job.salary_max ? job.salary_max / 1000 : 0).toFixed(0)}k
                      </span>
                    )}
                    {job.posted_at && (
                      <span className="flex items-center gap-1 text-slate-400">
                        <Clock className="w-3 h-3" /> {new Date(job.posted_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">{job.description}</p>

                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {job.required_skills?.slice(0, 6).map((skill, sidx) => (
                      <span
                        key={sidx}
                        className="text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-medium"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Actions Column */}
                <div className="flex md:flex-col items-center md:items-end gap-2.5 shrink-0">
                  <button
                    onClick={() => handleAnalyzeMatch(job.id)}
                    disabled={analyzingId === job.id}
                    className="flex items-center gap-1.5 bg-gradient-to-r from-sky-500 to-indigo-600 hover:opacity-95 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-sm transition-opacity"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{analyzingId === job.id ? 'Scoring...' : 'Analyze Match'}</span>
                  </button>

                  <button
                    onClick={() => handleInspectJob(job.id)}
                    className="flex items-center gap-1 text-xs text-slate-600 hover:text-slate-900 font-semibold px-3 py-2 rounded-lg hover:bg-slate-100 transition-colors"
                  >
                    <Info className="w-3.5 h-3.5 text-slate-500" />
                    <span>Normalized Details</span>
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center text-xs text-slate-500 space-y-3">
              <p>No jobs found matching your multi-criteria query.</p>
              <button
                onClick={handleSyncDiscovery}
                className="inline-flex items-center gap-1.5 bg-sky-50 text-sky-700 border border-sky-200 text-xs font-bold px-3.5 py-1.5 rounded-lg"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Sync Connectors Now
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Normalized Job Detail Modal */}
      {inspectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 animate-in fade-in zoom-in duration-150">
            <div className="flex items-start justify-between pb-4 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-sky-600 bg-sky-50 border border-sky-200 px-2 py-0.5 rounded uppercase">
                    Source: {inspectedJob.source}
                  </span>
                  <span className="text-xs text-slate-400">Ext ID: {inspectedJob.external_job_id}</span>
                </div>
                <h2 className="text-xl font-bold text-slate-900 mt-1">{inspectedJob.title}</h2>
                <div className="flex items-center gap-3 text-xs text-slate-600 mt-1 font-semibold">
                  <span className="flex items-center gap-1">
                    <Building className="w-3.5 h-3.5" /> {inspectedJob.company}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5" /> {inspectedJob.location} ({inspectedJob.remote_type})
                  </span>
                  {inspectedJob.salary_min && (
                    <span className="flex items-center gap-1 text-emerald-600 font-bold">
                      <DollarSign className="w-3.5 h-3.5" /> ${(inspectedJob.salary_min / 1000).toFixed(0)}k - ${(inspectedJob.salary_max ? inspectedJob.salary_max / 1000 : 0).toFixed(0)}k {inspectedJob.currency}
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => setInspectedJob(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="py-5 space-y-4 max-h-96 overflow-y-auto pr-1 text-xs">
              <div>
                <h4 className="font-bold uppercase tracking-wider text-slate-800 mb-1">Role Description</h4>
                <p className="text-slate-600 leading-relaxed whitespace-pre-line bg-slate-50 p-3.5 rounded-xl border border-slate-100">
                  {inspectedJob.description}
                </p>
              </div>

              <div>
                <h4 className="font-bold uppercase tracking-wider text-slate-800 mb-1">Required Skills</h4>
                <div className="flex flex-wrap gap-1.5">
                  {inspectedJob.skills.map((s, idx) => (
                    <span key={idx} className="bg-sky-50 text-sky-700 border border-sky-200 px-2.5 py-1 rounded-lg font-medium">
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
                <div>
                  <span className="font-bold text-slate-700 block">Experience Level</span>
                  <span className="text-slate-600">{inspectedJob.experience_required}</span>
                </div>
                <div>
                  <span className="font-bold text-slate-700 block">Education Required</span>
                  <span className="text-slate-600">{inspectedJob.education_required || "Bachelor's Degree"}</span>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">Official posting link</span>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setInspectedJob(null)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Close
                </button>
                <a
                  href={inspectedJob.application_url || '#'}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold bg-slate-900 hover:bg-slate-800 text-white rounded-lg transition-colors shadow-sm"
                >
                  <span>Open Official Application URL</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Match Analysis Modal */}
      {selectedMatch && (
        <MatchBreakdownModal
          match={selectedMatch}
          onClose={() => setSelectedMatch(null)}
          onApply={async (jobId) => {
            try {
              await api.createApplication({ job_id: jobId });
              alert('Application added to your tracker!');
              window.location.href = '/applications';
            } catch (e: any) {
              alert(e.message);
            }
          }}
        />
      )}
    </div>
  );
}
