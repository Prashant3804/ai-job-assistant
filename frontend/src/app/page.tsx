'use client';

import React, { useEffect, useState } from 'react';
import { Header } from '@/components/Header';
import { MetricCard } from '@/components/MetricCard';
import { MatchBreakdownModal } from '@/components/MatchBreakdownModal';
import {
  Search,
  Sparkles,
  Briefcase,
  Calendar,
  Award,
  Clock,
  ArrowUpRight,
  Building,
  MapPin,
  DollarSign,
  ChevronRight,
  Play,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Power,
  RotateCw,
} from 'lucide-react';
import { api } from '@/lib/api';
import { DashboardAnalytics, JobMatch } from '@/types';
import Link from 'next/link';

export default function DashboardPage() {
  const [data, setData] = useState<DashboardAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedMatch, setSelectedMatch] = useState<JobMatch | null>(null);
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
        text: `Routine run completed: ${res.applied_count} applied, ${res.manual_required_count} manual required out of ${res.matching_jobs} matching jobs.`,
      });
    } catch (err: any) {
      setFeedback({ type: 'error', text: err?.message || 'Failed to execute daily routine' });
    } finally {
      setTriggering(false);
    }
  }

  const metrics = data?.metrics || {
    jobs_found: 0,
    recommended_jobs: 0,
    applications_total: 0,
    interviews: 0,
    offers: 0,
    pending_applications: 0,
  };

  const routine = data?.auto_apply_routine;
  const lastRun = routine?.last_run;
  const recentApps = data?.recent_auto_apply_applications || [];

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Dashboard"
        subtitle="AI Candidate Pipeline & Opportunity Intelligence"
      />

      <div className="p-8 space-y-8">
        {/* Feedback Alert */}
        {feedback && (
          <div
            className={`p-4 rounded-xl text-xs font-semibold flex items-center justify-between transition-all ${
              feedback.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-rose-50 text-rose-800 border border-rose-200'
            }`}
          >
            <span>{feedback.text}</span>
            <button
              onClick={() => setFeedback(null)}
              className="text-slate-400 hover:text-slate-700 ml-4 font-bold"
            >
              &times;
            </button>
          </div>
        )}

        {/* 6 Required Dashboard Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <MetricCard
            title="Jobs Found"
            value={metrics.jobs_found}
            subtitle="Across authorized feeds"
            icon={Search}
            color="slate"
            badge="Live"
          />
          <MetricCard
            title="Recommended Jobs"
            value={metrics.recommended_jobs}
            subtitle="Compatibility > 80%"
            icon={Sparkles}
            color="blue"
            badge="High Fit"
          />
          <MetricCard
            title="Applications"
            value={metrics.applications_total}
            subtitle="Total in active funnel"
            icon={Briefcase}
            color="indigo"
          />
          <MetricCard
            title="Interviews"
            value={metrics.interviews}
            subtitle={metrics.interviews > 0 ? `${metrics.interviews} scheduled` : 'No upcoming interviews'}
            icon={Calendar}
            color="amber"
            badge={metrics.interviews > 0 ? 'Active' : undefined}
          />
          <MetricCard
            title="Offers"
            value={metrics.offers}
            subtitle={metrics.offers > 0 ? `${metrics.offers} active offers` : 'No active offers'}
            icon={Award}
            color="emerald"
            badge={metrics.offers > 0 ? 'Offer' : undefined}
          />
          <MetricCard
            title="Pending Applications"
            value={metrics.pending_applications}
            subtitle="Awaiting initial review"
            icon={Clock}
            color="purple"
          />
        </div>

        {/* Auto-Apply Daily Routine Section */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-slate-100">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <span className="text-xl">🤖</span> Auto-Apply
                </h3>
                {(routine?.auto_apply_enabled ?? routine?.enabled) ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    Active
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-600 border border-slate-200">
                    <span className="w-2 h-2 rounded-full bg-slate-400"></span>
                    Disabled
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Daily Schedule: <span className="font-semibold text-slate-700">Every day at 10:00 AM IST</span> • Automatically applies to all matching jobs without artificial limits
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => handleToggleRoutine(routine?.auto_apply_enabled ?? routine?.enabled ?? true)}
                disabled={toggling}
                className={`px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all flex items-center gap-1.5 ${
                  (routine?.auto_apply_enabled ?? routine?.enabled)
                    ? 'border-slate-200 text-slate-700 bg-white hover:bg-slate-50'
                    : 'border-emerald-300 text-emerald-700 bg-emerald-50 hover:bg-emerald-100'
                }`}
              >
                <Power className="w-3.5 h-3.5" />
                {toggling ? 'Updating...' : (routine?.auto_apply_enabled ?? routine?.enabled) ? 'Disable Auto-Apply' : 'Enable Auto-Apply'}
              </button>

              <button
                onClick={handleTriggerNow}
                disabled={triggering}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-sky-600 hover:bg-sky-500 active:bg-sky-700 text-white transition-all flex items-center gap-2 shadow-sm disabled:opacity-60"
              >
                {triggering ? (
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5 fill-current" />
                )}
                {triggering ? 'Running Routine...' : 'Trigger Now'}
              </button>

              <Link
                href="/auto-apply"
                className="px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 border border-slate-200 hover:border-slate-300 bg-slate-50 transition-all flex items-center gap-1"
              >
                View Auto-Apply Activity <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Schedule & Run Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-5">
            <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Next Scheduled Run</span>
              <div className="text-sm font-bold text-slate-800 mt-1 flex items-center gap-2">
                <Clock className="w-4 h-4 text-sky-500 shrink-0" />
                <span>{routine?.next_run_display || routine?.next_run_ist || 'Today at 10:00 AM IST'}</span>
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">Runs persistently on backend</span>
            </div>

            <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Last Run Status</span>
              <div className="text-sm font-bold text-slate-800 mt-1 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                <span className="capitalize">{lastRun?.status?.toLowerCase().replace(/_/g, ' ') || 'Ready for 10:00 AM'}</span>
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">
                {lastRun?.completed_at ? `Finished: ${new Date(lastRun.completed_at).toLocaleTimeString()}` : 'Next execution queued'}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Last Run Applications</span>
              <div className="text-sm font-bold text-slate-800 mt-1 flex items-center gap-3">
                <span className="text-emerald-600 font-extrabold">{lastRun?.applied_count ?? 0} Submitted</span>
                <span className="text-slate-300">•</span>
                <span className="text-amber-600 font-semibold">{lastRun?.manual_required_count ?? 0} Manual</span>
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">
                Out of {lastRun?.matching_jobs ?? 0} matching opportunities
              </span>
            </div>

            <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Duplicate Filtered</span>
              <div className="text-sm font-bold text-slate-800 mt-1">
                {lastRun?.already_applied_count ?? 0} skipped (already applied)
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">Strict duplicate prevention active</span>
            </div>
          </div>
        </div>

        {/* Two-Column Content Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column (2 cols): Recent Auto-Apply Applications + Top Recommended Jobs */}
          <div className="lg:col-span-2 space-y-8">
            {/* Recent Auto-Apply Applications */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <Briefcase className="w-4 h-4 text-indigo-500" />
                    Recent Auto-Apply Applications
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">Real applications processed by the automated routine</p>
                </div>
                <Link
                  href="/auto-apply"
                  className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center gap-1"
                >
                  View complete history <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              <div className="space-y-3">
                {recentApps.length > 0 ? (
                  recentApps.map((app) => (
                    <div
                      key={app.id}
                      className="p-4 rounded-xl border border-slate-100 hover:border-slate-300 hover:bg-slate-50/40 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-slate-900">{app.job_title || app.role_title}</span>
                          <span className="text-xs text-slate-400">•</span>
                          <span className="text-xs font-semibold text-slate-700 flex items-center gap-1">
                            <Building className="w-3.5 h-3.5 text-slate-400" /> {app.company_name}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-slate-500">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5 text-slate-400" /> {app.applied_at_display || app.applied_at_ist || 'Today'}
                          </span>
                          <span>•</span>
                          <span>Method: {app.submission_method}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-4 shrink-0">
                        <div className="text-right">
                          <div className="text-sm font-black text-sky-600">{(app.match_score ?? 0).toFixed(0)}%</div>
                          <div className="text-[10px] text-slate-400 uppercase font-medium">Match</div>
                        </div>

                        {app.status === 'APPLIED' || app.status === 'SUBMITTED' ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Applied ✓
                          </span>
                        ) : app.status === 'EXTERNAL_APPLICATION_REQUIRED' ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                            <ExternalLink className="w-3.5 h-3.5" /> Manual Required
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                            <AlertCircle className="w-3.5 h-3.5" /> {app.status}
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-slate-400 text-xs border border-dashed border-slate-200 rounded-xl">
                    No automated applications executed yet. The routine is scheduled for every day at 10:00 AM IST.
                  </div>
                )}
              </div>
            </div>

            {/* Top Recommended Opportunities */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-sky-500" />
                    Top Recommended Jobs
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">Ranked by explainable multi-factor AI scoring</p>
                </div>
                <Link
                  href="/recommended"
                  className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center gap-1"
                >
                  View all ({data?.top_recommendations?.length || 0}) <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              <div className="space-y-3">
                {data?.top_recommendations && data.top_recommendations.length > 0 ? (
                  data.top_recommendations.map((m) => (
                    <div
                      key={m.id}
                      onClick={() => setSelectedMatch(m)}
                      className="p-4 rounded-xl border border-slate-200/80 hover:border-sky-300 hover:bg-sky-50/30 transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-slate-900">{m.job.title}</span>
                          {m.overall_score >= 85 && (
                            <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold px-2 py-0.5 rounded-full">
                              Top Pick
                            </span>
                          )}
                        </div>
                        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                          <span className="flex items-center gap-1 font-medium text-slate-700">
                            <Building className="w-3.5 h-3.5" /> {m.job.company_name}
                          </span>
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3.5 h-3.5" /> {m.job.location || 'Remote'}
                          </span>
                          {m.job.salary_min && (
                            <span className="flex items-center gap-1 text-emerald-600 font-semibold">
                              <DollarSign className="w-3.5 h-3.5" /> ${(m.job.salary_min / 1000).toFixed(0)}k - ${(m.job.salary_max ? m.job.salary_max / 1000 : 0).toFixed(0)}k
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-4 shrink-0">
                        <div className="text-right">
                          <div className="text-lg font-black text-sky-600">{m.overall_score.toFixed(0)}%</div>
                          <div className="text-[10px] text-slate-400 uppercase font-medium">Match Fit</div>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedMatch(m);
                          }}
                          className="p-2 rounded-lg bg-slate-100 hover:bg-sky-100 text-slate-600 hover:text-sky-700 transition-colors"
                        >
                          <ArrowUpRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-10 text-slate-400 text-xs">
                    {loading ? 'Loading recommendations...' : 'No recommendations found yet'}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column (1 col): Preserved AI Assistant Actions */}
          <div className="space-y-6">
            {/* Quick Assistant Actions - KEPT INTACT */}
            <div className="bg-gradient-to-br from-slate-900 to-indigo-950 text-white rounded-2xl p-6 shadow-md border border-slate-800">
              <div className="flex items-center gap-2 text-sky-400 text-xs font-bold uppercase tracking-wider mb-2">
                <Sparkles className="w-4 h-4" /> AI Assistant Actions
              </div>
              <h4 className="text-sm font-semibold">Ready for your Stripe technical interview?</h4>
              <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                Generate practice questions tailored to Stripe financial infrastructure and your resume.
              </p>
              <Link
                href="/chat"
                className="mt-4 inline-flex items-center gap-2 bg-sky-500 hover:bg-sky-400 text-slate-950 text-xs font-bold px-4 py-2 rounded-lg transition-colors"
              >
                Launch Interview Prep <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Explainable Match Modal */}
      {selectedMatch && (
        <MatchBreakdownModal
          match={selectedMatch}
          onClose={() => setSelectedMatch(null)}
          onApply={() => {
            window.location.href = '/applications';
          }}
        />
      )}
    </div>
  );
}
