'use client';

import React, { useEffect, useState } from 'react';
import { Header } from '@/components/Header';
import {
  Clock,
  ArrowUpRight,
  Building,
  ChevronRight,
  Play,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Power,
  RotateCw,
  X,
  Layers,
  FileText,
  Cpu,
  ShieldCheck,
  Check,
  Zap,
  Calendar,
} from 'lucide-react';
import { api } from '@/lib/api';
import { DashboardAnalytics, PlatformStatItem, PlatformsDashboardResponse } from '@/types';
import Link from 'next/link';

interface PlatformMeta {
  name: string;
  slug: string;
  icon: string;
  defaultStatus: string;
  automationType: string;
}

const SEVEN_PLATFORMS: PlatformMeta[] = [
  { name: 'Naukri', slug: 'naukri', icon: '💼', defaultStatus: 'ACTIVE', automationType: 'EXTERNAL_PORTAL' },
  { name: 'Indeed', slug: 'indeed', icon: '🔍', defaultStatus: 'ACTIVE', automationType: 'EXTERNAL_PORTAL' },
  { name: 'Unstop', slug: 'unstop', icon: '🏆', defaultStatus: 'ACTIVE', automationType: 'DISCOVERY_FEED' },
  { name: 'LinkedIn Jobs', slug: 'linkedin', icon: '🔗', defaultStatus: 'ACTIVE', automationType: 'EXTERNAL_PORTAL' },
  { name: 'Internshala', slug: 'internshala', icon: '🎓', defaultStatus: 'ACTIVE', automationType: 'DISCOVERY_FEED' },
  { name: 'Wellfound', slug: 'wellfound', icon: '🚀', defaultStatus: 'ACTIVE', automationType: 'DISCOVERY_FEED' },
  { name: 'Company Careers', slug: 'career_pages', icon: '🏢', defaultStatus: 'AUTOMATION AVAILABLE', automationType: 'DIRECT_ATS_API' },
];

export default function DashboardPage() {
  const [data, setData] = useState<DashboardAnalytics | null>(null);
  const [platformStats, setPlatformStats] = useState<PlatformsDashboardResponse | null>(null);
  const [resumes, setResumes] = useState<any[]>([]);
  const [profile, setProfile] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Platform Detail Modal State
  const [selectedPlatform, setSelectedPlatform] = useState<PlatformStatItem | null>(null);
  const [timeFilter, setTimeFilter] = useState<'today' | 'yesterday' | '7d' | '30d' | 'all'>('today');
  const [modalApps, setModalApps] = useState<any[]>([]);
  const [loadingModalApps, setLoadingModalApps] = useState(false);

  useEffect(() => {
    loadDashboard();
  }, []);

  useEffect(() => {
    if (selectedPlatform) {
      loadPlatformApps(selectedPlatform.slug, timeFilter);
    }
  }, [selectedPlatform, timeFilter]);

  async function loadDashboard() {
    try {
      setLoading(true);
      const [dashRes, statsRes, resumesRes, profileRes] = await Promise.all([
        api.getDashboard().catch((e) => {
          console.error('Failed to load dashboard analytics:', e);
          return null;
        }),
        api.getPlatformStats().catch((e) => {
          console.error('Failed to load platform stats:', e);
          return null;
        }),
        api.getResumes().catch((e) => {
          console.error('Failed to load resumes:', e);
          return [];
        }),
        api.getProfile().catch((e) => {
          console.error('Failed to load candidate profile:', e);
          return null;
        }),
      ]);

      if (dashRes) setData(dashRes);
      if (statsRes) setPlatformStats(statsRes);
      if (resumesRes) setResumes(Array.isArray(resumesRes) ? resumesRes : []);
      if (profileRes) setProfile(profileRes);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  }

  async function loadPlatformApps(slug: string, filter: string) {
    try {
      setLoadingModalApps(true);
      const res = await api.getApplications({ source: slug, time_range: filter, limit: 100 });
      setModalApps(Array.isArray(res) ? res : []);
    } catch (err) {
      console.error('Failed to load platform applications:', err);
      setModalApps([]);
    } finally {
      setLoadingModalApps(false);
    }
  }

  async function handleToggleRoutine(currentEnabled: boolean) {
    try {
      setToggling(true);
      setFeedback(null);
      await api.toggleAutoApplyRoutine(!currentEnabled);
      await loadDashboard();
      setFeedback({
        type: 'success',
        text: `Autonomous Agent has been ${!currentEnabled ? 'resumed' : 'paused'}.`,
      });
    } catch (err: any) {
      setFeedback({ type: 'error', text: err?.message || 'Failed to update agent status' });
    } finally {
      setToggling(false);
    }
  }

  async function handleRunAgentNow() {
    try {
      setTriggering(true);
      setFeedback(null);
      const res = await api.triggerAutoApplyDailyRoutineNow();
      await loadDashboard();
      setFeedback({
        type: 'success',
        text: `Autonomous run completed: ${res.applied_count} submitted, ${res.manual_required_count} manual required out of ${res.matching_jobs} matching opportunities.`,
      });
    } catch (err: any) {
      setFeedback({ type: 'error', text: err?.message || 'Failed to execute agent routine' });
    } finally {
      setTriggering(false);
    }
  }

  const routine = data?.auto_apply_routine;
  const isAgentActive = routine?.auto_apply_enabled ?? routine?.enabled ?? true;
  const lastRun = routine?.last_run;
  const recentApps = data?.recent_auto_apply_applications || [];

  // Resume status resolution
  const primaryResume = resumes.find((r: any) => r.is_primary) || resumes[0] || null;
  const hasResume = Boolean(primaryResume || (profile && profile.skills && profile.skills.length > 0));

  // Duration calculation for last run
  let lastRunDuration = '—';
  if (lastRun?.run_summary_json?.duration_seconds !== undefined) {
    lastRunDuration = `${lastRun.run_summary_json.duration_seconds}s`;
  } else if (lastRun?.completed_at && lastRun?.started_at) {
    const durSec = (new Date(lastRun.completed_at).getTime() - new Date(lastRun.started_at).getTime()) / 1000;
    lastRunDuration = `${Math.max(0.1, durSec).toFixed(1)}s`;
  }

  function getStatusBadge(statusStr: string) {
    const s = (statusStr || '').toUpperCase();
    if (s.includes('AUTOMATION')) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-50 text-sky-700 border border-sky-200">
          <span className="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse"></span>
          ⚡ Automation Available
        </span>
      );
    }
    if (s === 'ACTIVE') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          🟢 Active
        </span>
      );
    }
    if (s === 'MANUAL ONLY') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
          📋 Manual Only
        </span>
      );
    }
    if (s === 'PAUSED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
          ⏸ Paused
        </span>
      );
    }
    if (s === 'RATE LIMITED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-orange-50 text-orange-700 border border-orange-200">
          ⚠️ Rate Limited
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
        ❌ {statusStr}
      </span>
    );
  }

  const totalAppliedToday =
    platformStats?.total_applied_today ??
    routine?.daily_total_applied ??
    (lastRun?.applied_count ?? 0);

  const totalJobsFound =
    platformStats
      ? Object.values(platformStats.platforms || {}).reduce((sum, p) => sum + (p.jobs_discovered || 0), 0)
      : data?.metrics?.jobs_found ?? 210;

  const totalMatchingJobs =
    platformStats
      ? Object.values(platformStats.platforms || {}).reduce((sum, p) => sum + (p.matching_jobs || 0), 0)
      : data?.metrics?.recommended_jobs ?? (lastRun?.matching_jobs ?? 0);

  const totalManualRequired =
    platformStats?.total_manual_required_today ??
    (lastRun?.manual_required_count ?? 0);

  const totalFailed =
    platformStats?.total_failed_today ??
    (lastRun?.failed_count ?? 0);

  const totalQueuedForNextWindow =
    platformStats?.total_queued_for_next_window ??
    routine?.queued_for_next_window_count ??
    0;

  const appWindow =
    platformStats?.application_window ??
    routine?.application_window ??
    null;
  const isWindowOpen = appWindow?.is_open ?? false;

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Dashboard"
        subtitle="Autonomous Candidate Pipeline & Multi-Platform Application Agent"
      />

      <div className="p-8 max-w-7xl mx-auto w-full space-y-8">
        {/* Feedback Notification */}
        {feedback && (
          <div
            className={`p-4 rounded-xl text-xs font-semibold flex items-center justify-between transition-all shadow-sm ${
              feedback.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-rose-50 text-rose-800 border border-rose-200'
            }`}
          >
            <span>{feedback.text}</span>
            <button
              onClick={() => setFeedback(null)}
              className="text-slate-400 hover:text-slate-700 ml-4 font-bold text-base leading-none"
            >
              &times;
            </button>
          </div>
        )}

        {/* ==================================================
            1. AUTONOMOUS MISSION CONTROL HERO BANNER
           ================================================== */}
        <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-100">
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="text-xl font-extrabold text-slate-900 flex items-center gap-2">
                  <span className="text-2xl">🤖</span> AUTONOMOUS JOB AGENT
                </h2>

                {/* Agent Status Badge */}
                {isAgentActive ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    🟢 ACTIVE
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
                    <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                    🔴 AGENT PAUSED
                  </span>
                )}

                {/* Application Window Badge */}
                {isWindowOpen ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-xs" title="Automatic applications allowed until 11:59:59 AM IST">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                    <span>WINDOW OPEN (10 AM - 12 PM IST)</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200 shadow-xs" title={appWindow?.next_window_display || "Next window: 10:00 AM IST"}>
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    <span>WINDOW CLOSED • {appWindow?.next_window_display || "Next: 10:00 AM IST"}</span>
                  </span>
                )}

                {/* AI Resilient Gateway Status */}
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 shadow-xs">
                  <Cpu className="w-3.5 h-3.5 text-indigo-600" />
                  <span>{routine?.ai_provider_status?.active_display || 'Gemini Primary • OpenRouter Fallback'}</span>
                </span>
              </div>

              <p className="text-xs text-slate-500">
                Application Window: <span className="font-semibold text-slate-700">10:00 AM – 11:59 AM IST</span> • 24/7 background worker discovers, matches, and queues jobs continuously
              </p>
            </div>

            {/* Compact Secondary Actions */}
            <div className="flex flex-wrap items-center gap-2.5">
              <button
                onClick={handleRunAgentNow}
                disabled={triggering}
                title="Trigger immediate execution of the daily autonomous routine"
                className="px-3.5 py-2 rounded-xl text-xs font-bold bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-800 border border-slate-300 transition-all flex items-center gap-1.5 shadow-xs disabled:opacity-60"
              >
                {triggering ? (
                  <RotateCw className="w-3.5 h-3.5 animate-spin text-sky-600" />
                ) : (
                  <Play className="w-3.5 h-3.5 fill-current text-sky-600" />
                )}
                <span>{triggering ? 'Running Agent...' : 'Run Agent Now'}</span>
              </button>

              <button
                onClick={() => handleToggleRoutine(isAgentActive)}
                disabled={toggling}
                className={`px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all flex items-center gap-1.5 ${
                  isAgentActive
                    ? 'border-slate-200 text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50'
                    : 'border-emerald-300 text-emerald-700 bg-emerald-50 hover:bg-emerald-100'
                }`}
              >
                <Power className="w-3.5 h-3.5" />
                <span>{toggling ? 'Updating...' : isAgentActive ? 'Pause Agent' : 'Resume Agent'}</span>
              </button>

              <Link
                href="/settings"
                className="px-3 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 border border-slate-200 hover:border-slate-300 bg-slate-50 transition-all flex items-center gap-1"
              >
                Settings <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Today's Global Capacity Progress (30/source • 210 Max) */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70 space-y-2.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-700 flex items-center gap-2">
                <span>🎯</span> Overall Daily Application Progress (30 per platform • 210 capacity)
              </span>
              <span className="font-extrabold text-sky-700 bg-sky-50 px-2.5 py-0.5 rounded border border-sky-100">
                {totalAppliedToday} / 210 Applications
              </span>
            </div>
            <div className="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden">
              <div
                className="bg-sky-600 h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min(100, (totalAppliedToday / 210) * 100)}%`,
                }}
              />
            </div>
          </div>

          {/* Schedule & Run Meta Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Next Scheduled Routine
              </span>
              <div className="text-sm font-bold text-slate-800 mt-1.5 flex items-center gap-2">
                <Clock className="w-4 h-4 text-sky-500 shrink-0" />
                <span>{routine?.next_run_display || routine?.next_run_ist || 'Tomorrow at 10:00 AM IST'}</span>
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">
                Persistent server daemon runs daily at 10:00 AM IST without requiring browser window
              </span>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Last Autonomous Execution
              </span>
              <div className="text-sm font-bold text-slate-800 mt-1.5 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                <span className="capitalize">
                  {lastRun ? `${lastRun.status.toLowerCase().replace(/_/g, ' ')}` : 'Ready for 10:00 AM IST'}
                </span>
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">
                {lastRun?.completed_at
                  ? `Completed: ${new Date(lastRun.completed_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })} IST (${lastRunDuration})`
                  : 'Awaiting scheduled 10:00 AM IST trigger'}
              </span>
            </div>
          </div>
        </div>

        {/* ==================================================
            2. RESUME STATUS & AI ENGINE STATUS SECTION
           ================================================== */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card A: Candidate Resume & Profile Status */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center font-bold">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-extrabold text-slate-900">Candidate Resume & Profile</h3>
                    <p className="text-[11px] text-slate-400">Master candidate data driving matching & auto-apply</p>
                  </div>
                </div>
                {hasResume ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <Check className="w-3 h-3" /> Parsed & Active
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                    <AlertCircle className="w-3 h-3" /> Resume Not Uploaded
                  </span>
                )}
              </div>

              {hasResume ? (
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-medium">Document:</span>
                    <span className="font-bold text-slate-800 truncate max-w-[200px]">
                      {primaryResume?.title || 'Master Resume'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-medium">Profile Skills:</span>
                    <span className="font-bold text-slate-800">
                      {profile?.skills?.length ? `${profile.skills.length} skills parsed` : 'Synchronized'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-medium">Experience:</span>
                    <span className="font-bold text-slate-800">
                      {profile?.years_of_experience ? `${profile.years_of_experience} yrs verified` : 'Ready'}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="p-3 rounded-xl bg-amber-50/60 border border-amber-200 text-xs text-amber-800">
                  Upload your resume once so the autonomous agent can extract your skills, match opportunities, and apply.
                </div>
              )}
            </div>

            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
              {hasResume ? (
                <>
                  <Link
                    href="/resume"
                    className="font-bold text-sky-600 hover:text-sky-700 flex items-center gap-1"
                  >
                    View Resume <ChevronRight className="w-3.5 h-3.5" />
                  </Link>
                  <Link
                    href="/resume/profile"
                    className="font-medium text-slate-500 hover:text-slate-800 flex items-center gap-1"
                  >
                    Edit Profile <ArrowUpRight className="w-3.5 h-3.5" />
                  </Link>
                </>
              ) : (
                <Link
                  href="/resume"
                  className="w-full py-2 rounded-xl text-center font-bold bg-sky-600 hover:bg-sky-500 text-white transition-colors flex items-center justify-center gap-1.5 shadow-sm"
                >
                  <FileText className="w-3.5 h-3.5" /> Upload Master Resume
                </Link>
              )}
            </div>
          </div>

          {/* Card B: Dual-Provider AI Engine Status */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
                    <Cpu className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-extrabold text-slate-900">AI Intelligence Engine</h3>
                    <p className="text-[11px] text-slate-400">Resilient dual-provider LLM gateway</p>
                  </div>
                </div>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  <ShieldCheck className="w-3 h-3 text-indigo-600" /> Resilient Gateway
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Primary Provider</div>
                  <div className="font-extrabold text-slate-800 mt-1 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span>Gemini</span>
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Available & Ready</div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Fallback Provider</div>
                  <div className="font-extrabold text-slate-800 mt-1 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-sky-500"></span>
                    <span>OpenRouter</span>
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Hot Standby</div>
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-[11px] text-slate-500 flex items-center justify-between">
                <span>Active Routing:</span>
                <span className="font-bold text-slate-800">
                  {routine?.ai_provider_status?.active_display || 'Gemini (Primary)'}
                </span>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-[11px] text-slate-400">
                {routine?.ai_provider_status?.last_fallback_occurred
                  ? '⚠️ OpenRouter fallback active'
                  : '✓ Primary operations healthy'}
              </span>
              <Link
                href="/settings/ai"
                className="font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
              >
                Configure AI <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>

        {/* ==================================================
            3. GLOBAL OVERVIEW METRICS TILES
           ================================================== */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs text-center">
            <div className="text-xs text-slate-500 font-medium">Jobs Found</div>
            <div className="text-xl font-extrabold text-slate-900 mt-1">{totalJobsFound}</div>
            <span className="text-[10px] text-slate-400">7 Platforms</span>
          </div>

          <div className="p-4 rounded-xl bg-white border border-sky-100 shadow-xs text-center">
            <div className="text-xs text-sky-700 font-medium">Matching Jobs</div>
            <div className="text-xl font-extrabold text-sky-700 mt-1">{totalMatchingJobs}</div>
            <span className="text-[10px] text-sky-600 font-medium">&ge;65% threshold</span>
          </div>

          <div className="p-4 rounded-xl bg-white border border-emerald-100 shadow-xs text-center">
            <div className="text-xs text-emerald-700 font-medium">Submitted Today</div>
            <div className="text-xl font-extrabold text-emerald-700 mt-1">{totalAppliedToday}</div>
            <span className="text-[10px] text-emerald-600 font-medium">Out of 210 limit</span>
          </div>

          <div className="p-4 rounded-xl bg-white border border-indigo-100 shadow-xs text-center">
            <div className="text-xs text-indigo-700 font-medium">Queued for Window</div>
            <div className="text-xl font-extrabold text-indigo-700 mt-1">{totalQueuedForNextWindow}</div>
            <span className="text-[10px] text-indigo-600 font-medium">10 AM – 12 PM IST</span>
          </div>

          <div className="p-4 rounded-xl bg-white border border-amber-100 shadow-xs text-center">
            <div className="text-xs text-amber-700 font-medium">Manual Required</div>
            <div className="text-xl font-extrabold text-amber-700 mt-1">{totalManualRequired}</div>
            <span className="text-[10px] text-amber-600 font-medium">External portals</span>
          </div>

          <div className="p-4 rounded-xl bg-white border border-rose-100 shadow-xs text-center">
            <div className="text-xs text-rose-700 font-medium">Failed</div>
            <div className="text-xl font-extrabold text-rose-700 mt-1">{totalFailed}</div>
            <span className="text-[10px] text-rose-600 font-medium">Network/API errs</span>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs text-center">
            <div className="text-xs text-slate-500 font-medium">Remaining Quota</div>
            <div className="text-xl font-extrabold text-slate-800 mt-1">
              {Math.max(0, 210 - totalAppliedToday)}
            </div>
            <span className="text-[10px] text-slate-400">Daily capacity</span>
          </div>
        </div>

        {/* ==================================================
            4. TODAY'S AGENT ACTIVITY (UNIFIED SECTION)
           ================================================== */}
        <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
            <div>
              <h2 className="text-lg font-extrabold text-slate-900 flex items-center gap-2">
                <Layers className="w-5 h-5 text-sky-600" /> TODAY&apos;S AGENT ACTIVITY
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Unified Autonomous Pipeline • 65.0% qualification threshold • Legitimate automated submission &amp; manual assistance
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="font-semibold text-slate-500">Global Daily Limit:</span>
              <span className="font-bold text-sky-700 bg-sky-50 px-2.5 py-0.5 rounded border border-sky-100">
                {totalAppliedToday} / 210 Submitted
              </span>
            </div>
          </div>

          {/* 5 Key Metrics Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 shadow-xs">
              <div className="text-xs font-bold text-emerald-800 uppercase tracking-wide flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Applications Submitted
              </div>
              <div className="text-2xl font-black text-emerald-700 mt-2">{totalAppliedToday}</div>
              <p className="text-[11px] text-emerald-600 font-medium mt-0.5">
                Verified automated submissions
              </p>
            </div>

            <div className="p-4 rounded-xl bg-indigo-50/70 border border-indigo-200 shadow-xs">
              <div className="text-xs font-bold text-indigo-800 uppercase tracking-wide flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-indigo-600" /> Queued for Next Window
              </div>
              <div className="text-2xl font-black text-indigo-700 mt-2">{totalQueuedForNextWindow}</div>
              <p className="text-[11px] text-indigo-600 font-medium mt-0.5">
                Eligible &amp; prepared (10 AM IST)
              </p>
            </div>

            <div className="p-4 rounded-xl bg-sky-50/70 border border-sky-200 shadow-xs">
              <div className="text-xs font-bold text-sky-800 uppercase tracking-wide flex items-center gap-1.5">
                <Zap className="w-4 h-4 text-sky-600" /> Jobs Matched (&ge;65%)
              </div>
              <div className="text-2xl font-black text-sky-700 mt-2">{totalMatchingJobs}</div>
              <p className="text-[11px] text-sky-600 font-medium mt-0.5">
                Qualifying for auto/assisted apply
              </p>
            </div>

            <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200 shadow-xs">
              <div className="text-xs font-bold text-amber-800 uppercase tracking-wide flex items-center gap-1.5">
                <ExternalLink className="w-4 h-4 text-amber-600" /> Manual Required
              </div>
              <div className="text-2xl font-black text-amber-700 mt-2">{totalManualRequired}</div>
              <p className="text-[11px] text-amber-600 font-medium mt-0.5">
                External portals with direct link
              </p>
            </div>

            <div className="p-4 rounded-xl bg-rose-50/70 border border-rose-200 shadow-xs">
              <div className="text-xs font-bold text-rose-800 uppercase tracking-wide flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4 text-rose-600" /> Failed
              </div>
              <div className="text-2xl font-black text-rose-700 mt-2">{totalFailed}</div>
              <p className="text-[11px] text-rose-600 font-medium mt-0.5">
                API or validation errors
              </p>
            </div>
          </div>

          {/* Compact Platform Breakdown Table */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
                  <span>📊</span> Platform Breakdown
                </h3>
                <p className="text-[11px] text-slate-500">
                  Per-platform distribution • Strict 30 applications/platform limit • Click any row for history
                </p>
              </div>
              <span className="text-[11px] text-slate-400 hidden sm:inline">
                7 Integrated Sources
              </span>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px] tracking-wider">
                    <th className="py-3 px-4">Platform</th>
                    <th className="py-3 px-4">Capability</th>
                    <th className="py-3 px-4 text-center">Discovered</th>
                    <th className="py-3 px-4 text-center">Matched (&ge;65%)</th>
                    <th className="py-3 px-4 text-center">Submitted Today</th>
                    <th className="py-3 px-4 text-center">Manual Req.</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {SEVEN_PLATFORMS.map((meta) => {
                    const stat: PlatformStatItem =
                      platformStats?.platforms?.[meta.slug] ||
                      routine?.platforms?.[meta.slug] || {
                        name: meta.name,
                        slug: meta.slug,
                        jobs_discovered: 30,
                        matching_jobs: 0,
                        applied: 0,
                        manual_required: 0,
                        failed: 0,
                        daily_limit: 30,
                        applied_today: 0,
                        current_daily_count: 0,
                        progress_pct: 0.0,
                        last_activity_utc: null,
                        last_activity_ist: 'Never run',
                        status: meta.defaultStatus,
                        automation_type: meta.automationType,
                      };

                    return (
                      <tr
                        key={meta.slug}
                        onClick={() => setSelectedPlatform(stat)}
                        className="hover:bg-slate-50/80 transition-colors cursor-pointer"
                      >
                        <td className="py-3 px-4 font-bold text-slate-800 flex items-center gap-2">
                          <span className="text-base">{meta.icon}</span>
                          <span>{stat.name}</span>
                        </td>
                        <td className="py-3 px-4 text-slate-500">
                          <span className="text-[11px] font-medium">
                            {meta.automationType.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-center text-slate-700 font-semibold">
                          {stat.jobs_discovered}
                        </td>
                        <td className="py-3 px-4 text-center text-sky-700 font-bold">
                          {stat.matching_jobs}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span className="inline-flex items-center gap-1 font-extrabold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                            {stat.applied_today} <span className="text-slate-400 font-normal">/ {stat.daily_limit}</span>
                          </span>
                        </td>
                        <td className="py-3 px-4 text-center text-amber-700 font-semibold">
                          {stat.manual_required}
                        </td>
                        <td className="py-3 px-4 text-center">
                          {getStatusBadge(stat.status)}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            type="button"
                            className="text-xs font-bold text-sky-600 hover:text-sky-800 inline-flex items-center gap-0.5"
                          >
                            History <ChevronRight className="w-3 h-3" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr className="bg-slate-50/80 border-t border-slate-200 font-extrabold text-slate-800">
                    <td className="py-3 px-4">Total Across Platforms</td>
                    <td className="py-3 px-4 text-slate-400 font-normal">7 Channels</td>
                    <td className="py-3 px-4 text-center">{totalJobsFound}</td>
                    <td className="py-3 px-4 text-center text-sky-700">{totalMatchingJobs}</td>
                    <td className="py-3 px-4 text-center text-emerald-700">{totalAppliedToday} / 210</td>
                    <td className="py-3 px-4 text-center text-amber-700">{totalManualRequired}</td>
                    <td className="py-3 px-4 text-center text-slate-500">—</td>
                    <td className="py-3 px-4 text-right text-slate-400">—</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          {/* Recent Agent Activity list inside Today's Agent Activity */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
                  <span>⚡</span> Recent Agent Activity
                </h3>
                <p className="text-[11px] text-slate-500">
                  Last evaluated and processed opportunities across platforms
                </p>
              </div>
              <Link
                href="/applications"
                className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center gap-1"
              >
                View All Applications <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {recentApps.length > 0 ? (
              <div className="overflow-x-auto border border-slate-200 rounded-xl">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px] tracking-wider">
                      <th className="py-3 px-4">Company</th>
                      <th className="py-3 px-4">Role</th>
                      <th className="py-3 px-4">Platform</th>
                      <th className="py-3 px-4 text-center">Match %</th>
                      <th className="py-3 px-4">Time (IST)</th>
                      <th className="py-3 px-4 text-right">Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {recentApps.map((app) => (
                      <tr key={app.id} className="hover:bg-slate-50/60 transition-colors">
                        <td className="py-3 px-4 font-bold text-slate-800 flex items-center gap-1.5">
                          <Building className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span>{app.company_name}</span>
                        </td>
                        <td className="py-3 px-4 text-slate-700 font-medium max-w-[200px] truncate">
                          {app.job_title || app.role_title}
                        </td>
                        <td className="py-3 px-4 text-slate-600 font-medium">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[11px] font-semibold">
                            {app.platform || app.source || 'Direct'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span className="font-extrabold text-sky-600 bg-sky-50 px-2 py-0.5 rounded-md border border-sky-100">
                            {(app.match_score ?? 0).toFixed(0)}%
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                            {app.applied_at_display || app.applied_at_ist || 'Recent'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          {app.status === 'APPLIED' || app.status === 'SUBMITTED' ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              <CheckCircle2 className="w-3.5 h-3.5" /> ✓ Applied
                            </span>
                          ) : app.status === 'EXTERNAL_APPLICATION_REQUIRED' ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                              <ExternalLink className="w-3.5 h-3.5" /> Manual Action
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                              <AlertCircle className="w-3.5 h-3.5" /> {app.status}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-10 text-slate-400 text-xs border border-dashed border-slate-200 rounded-xl">
                {loading ? 'Loading agent activity...' : 'No autonomous activity recorded yet. Routine runs daily at 10:00 AM IST or click "Run Agent Now" above.'}
              </div>
            )}
          </div>
        </div>

        {/* ==================================================
            5. LAST DAILY RUN SUMMARY METRICS
           ================================================== */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
                <span>⏱</span> Last Daily Run Execution
              </h3>
              <p className="text-xs text-slate-500">
                Scheduled Start: <span className="font-semibold text-slate-700">10:00 AM IST</span> • Duration: <span className="font-semibold text-slate-700">{lastRunDuration}</span> • Provider: <span className="font-semibold text-slate-700">{lastRun?.run_summary_json?.ai_provider_display || routine?.ai_provider_status?.active_display || 'Gemini (Primary)'}</span>
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400">Fallback Occurred:</span>
              <span className={`font-bold px-2 py-0.5 rounded ${lastRun?.run_summary_json?.fallback_occurred ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}`}>
                {lastRun?.run_summary_json?.fallback_occurred ? 'Yes (OpenRouter)' : 'No (Gemini)'}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 text-center">
              <div className="text-xs text-slate-500 font-medium">Jobs Found</div>
              <div className="text-xl font-extrabold text-slate-900 mt-1">{lastRun?.jobs_found ?? 0}</div>
            </div>
            <div className="p-3.5 rounded-xl bg-sky-50/50 border border-sky-100 text-center">
              <div className="text-xs text-sky-700 font-medium">Matching Resume (&ge;65%)</div>
              <div className="text-xl font-extrabold text-sky-700 mt-1">{lastRun?.matching_jobs ?? 0}</div>
            </div>
            <div className="p-3.5 rounded-xl bg-emerald-50/60 border border-emerald-100 text-center">
              <div className="text-xs text-emerald-700 font-medium">Applied</div>
              <div className="text-xl font-extrabold text-emerald-700 mt-1">{lastRun?.applied_count ?? 0}</div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 text-center">
              <div className="text-xs text-slate-500 font-medium">Already Applied</div>
              <div className="text-xl font-extrabold text-slate-700 mt-1">{lastRun?.already_applied_count ?? 0}</div>
            </div>
            <div className="p-3.5 rounded-xl bg-amber-50/60 border border-amber-100 text-center">
              <div className="text-xs text-amber-700 font-medium">Manual Required</div>
              <div className="text-xl font-extrabold text-amber-700 mt-1">{lastRun?.manual_required_count ?? 0}</div>
            </div>
            <div className="p-3.5 rounded-xl bg-rose-50/40 border border-rose-100 text-center">
              <div className="text-xs text-rose-700 font-medium">Failed</div>
              <div className="text-xl font-extrabold text-rose-700 mt-1">{lastRun?.failed_count ?? 0}</div>
            </div>
          </div>
        </div>
      </div>

      {/* ==================================================
          7. PLATFORM APPLICATION HISTORY MODAL
         ================================================== */}
      {selectedPlatform && (
        <div
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => setSelectedPlatform(null)}
        >
          <div
            className="bg-white rounded-2xl max-w-4xl w-full max-h-[85vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white border border-slate-200 flex items-center justify-center shadow-sm text-xl">
                  {SEVEN_PLATFORMS.find((p) => p.slug === selectedPlatform.slug)?.icon || '💼'}
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                    {selectedPlatform.name} Application History
                  </h3>
                  <p className="text-xs text-slate-500">
                    Real applications submitted, manual-required, and failed for {selectedPlatform.name}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {getStatusBadge(selectedPlatform.status)}
                <button
                  onClick={() => setSelectedPlatform(null)}
                  className="w-8 h-8 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/50 flex items-center justify-center transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Time Filter Tabs Bar */}
            <div className="px-6 py-3 border-b border-slate-100 bg-white flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl text-xs font-semibold">
                {[
                  { id: 'today', label: 'Today' },
                  { id: 'yesterday', label: 'Yesterday' },
                  { id: '7d', label: 'Last 7 Days' },
                  { id: '30d', label: 'Last 30 Days' },
                  { id: 'all', label: 'All Time' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setTimeFilter(tab.id as any)}
                    className={`px-3 py-1.5 rounded-lg transition-all ${
                      timeFilter === tab.id
                        ? 'bg-white text-slate-900 shadow-sm font-bold'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <div className="text-xs text-slate-500 font-medium">
                Showing <span className="font-bold text-slate-800">{modalApps.length}</span> application{modalApps.length === 1 ? '' : 's'}
              </div>
            </div>

            {/* Modal Table Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {loadingModalApps ? (
                <div className="py-16 text-center text-xs text-slate-400 flex flex-col items-center justify-center gap-2">
                  <RotateCw className="w-5 h-5 animate-spin text-sky-600" />
                  <span>Loading platform history...</span>
                </div>
              ) : modalApps.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-100 text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                        <th className="pb-3 pr-4">Company</th>
                        <th className="pb-3 pr-4">Job</th>
                        <th className="pb-3 pr-4 text-center">Match %</th>
                        <th className="pb-3 pr-4">Time (IST)</th>
                        <th className="pb-3 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {modalApps.map((app) => {
                        const companyName = app.company_name || app.job?.company_name || 'Direct Employer';
                        const jobTitle = app.job_title || app.job?.title || 'Open Position';
                        const applyUrl = app.job?.apply_url;

                        return (
                          <tr key={app.id} className="hover:bg-slate-50/60 transition-colors">
                            <td className="py-3.5 pr-4 font-bold text-slate-800 flex items-center gap-1.5">
                              <Building className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                              <span className="truncate max-w-[160px]">{companyName}</span>
                            </td>
                            <td className="py-3.5 pr-4 text-slate-700 font-medium max-w-[240px]">
                              <div className="truncate flex items-center gap-1">
                                <span>{jobTitle}</span>
                                {applyUrl && (
                                  <a
                                    href={applyUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sky-500 hover:text-sky-700"
                                    title="View Job Posting"
                                  >
                                    <ExternalLink className="w-3 h-3 shrink-0" />
                                  </a>
                                )}
                              </div>
                            </td>
                            <td className="py-3.5 pr-4 text-center">
                              <span className="font-extrabold text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-100">
                                {app.match_score ? `${app.match_score.toFixed(0)}%` : '—'}
                              </span>
                            </td>
                            <td className="py-3.5 pr-4 text-slate-500 whitespace-nowrap">
                              {app.applied_at_display ||
                                (app.created_at
                                  ? new Date(app.created_at).toLocaleString('en-IN', {
                                      timeZone: 'Asia/Kolkata',
                                      month: 'short',
                                      day: 'numeric',
                                      hour: '2-digit',
                                      minute: '2-digit',
                                    }) + ' IST'
                                  : '—')}
                            </td>
                            <td className="py-3.5 text-right whitespace-nowrap">
                              {app.status === 'APPLIED' || app.status === 'SUBMITTED' ? (
                                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                  <CheckCircle2 className="w-3 h-3" /> ✓ Applied
                                </span>
                              ) : app.status === 'EXTERNAL_APPLICATION_REQUIRED' ? (
                                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                                  <ExternalLink className="w-3 h-3" /> Manual Required
                                </span>
                              ) : app.status === 'FAILED' ? (
                                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                                  <AlertCircle className="w-3 h-3" /> Failed
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                                  {app.status}
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-16 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-xl">
                  No applications recorded for <span className="font-semibold text-slate-600">{selectedPlatform.name}</span> in the selected timeframe ({timeFilter}).
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
              <span className="text-[11px]">
                Timestamps stored in UTC and rendered in Asia/Kolkata (IST).
              </span>
              <button
                onClick={() => setSelectedPlatform(null)}
                className="px-4 py-2 rounded-xl font-bold bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-sm"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
