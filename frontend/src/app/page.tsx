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
  TrendingUp,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';
import { api } from '@/lib/api';
import { DashboardAnalytics, JobMatch } from '@/types';
import Link from 'next/link';

export default function DashboardPage() {
  const [data, setData] = useState<DashboardAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedMatch, setSelectedMatch] = useState<JobMatch | null>(null);

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

  const metrics = data?.metrics || {
    jobs_found: 6,
    recommended_jobs: 3,
    applications_total: 4,
    interviews: 1,
    offers: 1,
    pending_applications: 2,
  };

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Dashboard"
        subtitle="AI Candidate Pipeline & Opportunity Intelligence"
      />

      <div className="p-8 space-y-8">
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
            subtitle="1 scheduled this week"
            icon={Calendar}
            color="amber"
            badge="Active"
          />
          <MetricCard
            title="Offers"
            value={metrics.offers}
            subtitle="Anthropic ($245k)"
            icon={Award}
            color="emerald"
            badge="Offer"
          />
          <MetricCard
            title="Pending Applications"
            value={metrics.pending_applications}
            subtitle="Awaiting initial review"
            icon={Clock}
            color="purple"
          />
        </div>

        {/* Top Recommendations & Funnel Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Top Recommended Opportunities (2 cols) */}
          <div className="lg:col-span-2 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
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
                <div className="text-center py-10 text-slate-400 text-xs">Loading recommendations...</div>
              )}
            </div>
          </div>

          {/* Right Column: Funnel & Quick Actions */}
          <div className="space-y-6">
            {/* Conversion Funnel */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 mb-4">
                <TrendingUp className="w-4 h-4 text-emerald-500" />
                Pipeline Funnel
              </h3>

              <div className="space-y-3">
                {Object.entries(data?.funnel || { Draft: 1, Submitted: 0, 'Under Review': 1, Interview: 1, Offer: 1 }).map(([stage, count]) => (
                  <div key={stage} className="flex items-center justify-between text-xs">
                    <span className="font-medium text-slate-600">{stage}</span>
                    <div className="flex items-center gap-3 flex-1 max-w-[140px] ml-4">
                      <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-indigo-500 h-full rounded-full"
                          style={{ width: `${Math.min(100, Math.max(15, count * 25))}%` }}
                        ></div>
                      </div>
                      <span className="font-bold text-slate-900 w-4 text-right">{count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Assistant Actions */}
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
