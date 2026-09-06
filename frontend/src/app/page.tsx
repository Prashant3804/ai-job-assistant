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
  Sparkles,
} from 'lucide-react';
import { api } from '@/lib/api';
import { DashboardAnalytics } from '@/types';
import Link from 'next/link';

export default function DashboardPage() {
  const [data, setData] = useState<DashboardAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      setLoading(true);
      const res = await api.getDashboard();
      setData(res);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
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
        text: `Daily Auto-Apply routine has been ${!currentEnabled ? 'activated' : 'disabled'}.`,
      });
    } catch (err: any) {
      setFeedback({ type: 'error', text: err?.message || 'Failed to toggle Auto-Apply routine' });
    } finally {
      setToggling(false);
    }
  }

  async function handleTriggerNow() {
    try {
      setTriggering(true);
      setFeedback(null);
      const res = await api.triggerAutoApplyDailyRoutineNow();
      await loadDashboard();
      setFeedback({
        type: 'success',
        text: `Routine completed: ${res.applied_count} applied, ${res.manual_required_count} manual required out of ${res.matching_jobs} matching opportunities.`,
      });
    } catch (err: any) {
      setFeedback({ type: 'error', text: err?.message || 'Failed to execute daily routine' });
    } finally {
      setTriggering(false);
    }
  }

  const routine = data?.auto_apply_routine;
  const isAutoApplyActive = routine?.auto_apply_enabled ?? routine?.enabled ?? true;
  const lastRun = routine?.last_run;
  const recentApps = data?.recent_auto_apply_applications || [];

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Dashboard"
        subtitle="Automated Daily Candidate Pipeline & Application Management"
      />

      <div className="p-8 max-w-6xl mx-auto w-full space-y-8">
        {/* Feedback Alert */}
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
            1. MAIN SECTION: 🤖 AUTO-APPLY
           ================================================== */}
        <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
          {/* Header Row: Title, Status, and Controls */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-100">
            <div className="space-y-1.5">
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-extrabold text-slate-900 flex items-center gap-2">
                  <span className="text-2xl">🤖</span> AUTO-APPLY
                </h2>
                {isAutoApplyActive ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    🟢 Auto-Apply Active
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-600 border border-slate-200">
                    <span className="w-2 h-2 rounded-full bg-slate-400"></span>
                    ⚪ Auto-Apply Disabled
                  </span>
                )}

                {/* AI Engine Status Pill */}
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 shadow-sm">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      routine?.ai_provider_status?.last_fallback_occurred
                        ? 'bg-amber-500'
                        : 'bg-indigo-500 animate-pulse'
                    }`}
                  ></span>
                  <span>{routine?.ai_provider_status?.active_display || 'Gemini (Primary)'}</span>
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Daily Schedule: <span className="font-semibold text-slate-700">Every day at 10:00 AM IST</span> • Automatically matches and processes all eligible jobs
              </p>
            </div>

            {/* Quick Actions */}
            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={handleTriggerNow}
                disabled={triggering}
                className="px-4 py-2.5 rounded-xl text-xs font-bold bg-sky-600 hover:bg-sky-500 active:bg-sky-700 text-white transition-all flex items-center gap-2 shadow-sm disabled:opacity-60"
              >
                {triggering ? (
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5 fill-current" />
                )}
                {triggering ? 'Running Routine...' : 'Trigger Now'}
              </button>

              <button
                onClick={() => handleToggleRoutine(isAutoApplyActive)}
                disabled={toggling}
                className={`px-4 py-2.5 rounded-xl text-xs font-semibold border transition-all flex items-center gap-1.5 ${
                  isAutoApplyActive
                    ? 'border-slate-200 text-slate-700 bg-white hover:bg-slate-50'
                    : 'border-emerald-300 text-emerald-700 bg-emerald-50 hover:bg-emerald-100'
                }`}
              >
                <Power className="w-3.5 h-3.5" />
                {toggling ? 'Updating...' : isAutoApplyActive ? 'Disable Auto-Apply' : 'Enable Auto-Apply'}
              </button>

              <Link
                href="/auto-apply"
                className="px-3.5 py-2.5 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 border border-slate-200 hover:border-slate-300 bg-slate-50 transition-all flex items-center gap-1"
              >
                Settings <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Today's Applications Capacity Bar (210 Total Max) */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70 space-y-2.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-700 flex items-center gap-2">
                <span>🎯</span> Today&apos;s Application Progress (30 per source • 210 capacity)
              </span>
              <span className="font-extrabold text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-100">
                {(routine?.daily_total_applied ?? ((lastRun?.applied_count ?? 0) + (lastRun?.manual_required_count ?? 0)))} / 210 Applications
              </span>
            </div>
            <div className="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden">
              <div
                className="bg-sky-600 h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min(
                    100,
                    (((routine?.daily_total_applied ??
                      (lastRun?.applied_count ?? 0) + (lastRun?.manual_required_count ?? 0)) /
                      210) *
                      100)
                  )}%`,
                }}
              />
            </div>
          </div>

          {/* 7 Job Sources Daily Pipeline (30 per source) */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              7 Job Sources Daily Quota (30 Applications / Source)
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
              {[
                { name: 'Naukri', key: 'naukri' },
                { name: 'Indeed', key: 'indeed' },
                { name: 'Unstop', key: 'unstop' },
                { name: 'LinkedIn', key: 'linkedin' },
                { name: 'Internshala', key: 'internshala' },
                { name: 'Wellfound', key: 'wellfound' },
                { name: 'Company Careers', key: 'career_pages' },
              ].map((source) => {
                const count =
                  routine?.source_counters?.[source.key] ??
                  lastRun?.run_summary_json?.source_counts?.[source.key] ??
                  0;
                const limit = routine?.source_limits?.[source.key] ?? 30;
                const pct = Math.min(100, (count / limit) * 100);
                return (
                  <div
                    key={source.key}
                    className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col justify-between"
                  >
                    <div className="text-[11px] font-bold text-slate-700 truncate">{source.name}</div>
                    <div className="mt-1 flex items-baseline justify-between">
                      <span className="text-base font-extrabold text-slate-900">{count}</span>
                      <span className="text-[10px] text-slate-400 font-semibold">/ {limit}</span>
                    </div>
                    <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden mt-1.5">
                      <div
                        className={`h-full rounded-full transition-all ${
                          count > 0 ? 'bg-emerald-500' : 'bg-slate-300'
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Schedule & Last Run Dates */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Next Scheduled Run
              </span>
              <div className="text-sm font-bold text-slate-800 mt-1.5 flex items-center gap-2">
                <Clock className="w-4 h-4 text-sky-500 shrink-0" />
                <span>{routine?.next_run_display || routine?.next_run_ist || 'Tomorrow at 10:00 AM IST'}</span>
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">Runs persistently on backend server (no browser needed)</span>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Last Run Status
              </span>
              <div className="text-sm font-bold text-slate-800 mt-1.5 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                <span className="capitalize">
                  {lastRun ? `${lastRun.status.toLowerCase().replace(/_/g, ' ')}` : 'Ready for 10:00 AM'}
                </span>
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">
                {lastRun?.completed_at
                  ? `Completed: ${new Date(lastRun.completed_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })} IST`
                  : 'Awaiting scheduled 10:00 AM trigger'}
              </span>
            </div>
          </div>

          {/* Last Run Summary Metrics (Real Database Values) */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Last Run Summary</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 text-center">
                <div className="text-xs text-slate-500 font-medium">Jobs Found</div>
                <div className="text-xl font-extrabold text-slate-900 mt-1">{lastRun?.jobs_found ?? 0}</div>
              </div>
              <div className="p-3.5 rounded-xl bg-sky-50/50 border border-sky-100 text-center">
                <div className="text-xs text-sky-700 font-medium">Matching Resume</div>
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
            2. RECENT AUTO-APPLY ACTIVITY
           ================================================== */}
        <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <span className="text-xl">🤖</span> RECENT AUTO-APPLY ACTIVITY
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">Real application records stored in PostgreSQL with Asia/Kolkata timestamps</p>
            </div>
            <Link
              href="/applications"
              className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center gap-1"
            >
              View All Applications <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-3">
            {recentApps.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                      <th className="pb-3 pr-4">Company</th>
                      <th className="pb-3 pr-4">Role</th>
                      <th className="pb-3 pr-4 text-center">Match Score</th>
                      <th className="pb-3 pr-4">Time (IST)</th>
                      <th className="pb-3 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {recentApps.map((app) => (
                      <tr key={app.id} className="hover:bg-slate-50/60 transition-colors">
                        <td className="py-3.5 pr-4 font-bold text-slate-800 flex items-center gap-1.5">
                          <Building className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span>{app.company_name}</span>
                        </td>
                        <td className="py-3.5 pr-4 text-slate-700 font-medium max-w-[220px] truncate">
                          {app.job_title || app.role_title}
                        </td>
                        <td className="py-3.5 pr-4 text-center">
                          <span className="font-extrabold text-sky-600 bg-sky-50 px-2 py-0.5 rounded-md border border-sky-100">
                            {(app.match_score ?? 0).toFixed(0)}%
                          </span>
                        </td>
                        <td className="py-3.5 pr-4 text-slate-500 flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span>{app.applied_at_display || app.applied_at_ist || 'Recent'}</span>
                        </td>
                        <td className="py-3.5 text-right">
                          {app.status === 'APPLIED' || app.status === 'SUBMITTED' ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              <CheckCircle2 className="w-3.5 h-3.5" /> ✓ Applied
                            </span>
                          ) : app.status === 'EXTERNAL_APPLICATION_REQUIRED' ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                              <ExternalLink className="w-3.5 h-3.5" /> Manual
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
                {loading ? 'Loading application activity...' : 'No auto-apply activity recorded yet. The routine runs every day at 10:00 AM IST.'}
              </div>
            )}
          </div>

          <div className="pt-2 flex justify-end">
            <Link
              href="/applications"
              className="text-xs font-bold text-sky-600 hover:text-sky-700 inline-flex items-center gap-1"
            >
              View All Applications &rarr;
            </Link>
          </div>
        </div>

        {/* ==================================================
            3. AI ASSISTANT ACTIONS (KEPT INTACT)
           ================================================== */}
        <div className="bg-gradient-to-br from-slate-900 to-indigo-950 text-white rounded-2xl p-6 sm:p-8 shadow-md border border-slate-800">
          <div className="flex items-center gap-2 text-sky-400 text-xs font-bold uppercase tracking-wider mb-2">
            <Sparkles className="w-4 h-4" /> AI Assistant Actions
          </div>
          <h3 className="text-base font-semibold">Ready for your Stripe technical interview?</h3>
          <p className="text-xs text-slate-300 mt-1 leading-relaxed max-w-2xl">
            Generate practice questions tailored to Stripe financial infrastructure and your resume.
          </p>
          <Link
            href="/chat"
            className="mt-4 inline-flex items-center gap-2 bg-sky-500 hover:bg-sky-400 text-slate-950 text-xs font-bold px-4 py-2.5 rounded-lg transition-colors shadow-sm"
          >
            Launch Interview Prep <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
}

