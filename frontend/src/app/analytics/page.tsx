'use client';

import React, { useEffect, useState } from 'react';
import { Header } from '@/components/Header';
import {
  BarChart3,
  TrendingUp,
  Award,
  PieChart,
  Sparkles,
  CheckCircle2,
  Calendar,
} from 'lucide-react';
import { api } from '@/lib/api';
import { DashboardAnalytics } from '@/types';

export default function AnalyticsPage() {
  const [data, setData] = useState<DashboardAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, []);

  async function loadAnalytics() {
    try {
      setLoading(true);
      const res = await api.getDashboard();
      setData(res);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    } finally {
      setLoading(false);
    }
  }

  const topSkills = data?.top_skills_in_demand || [];

  const totalApps = data?.metrics?.applications_total || 0;
  const interviewsCount = data?.metrics?.interviews || 0;
  const offersCount = data?.metrics?.offers || 0;
  const interviewRate = totalApps > 0 ? ((interviewsCount / totalApps) * 100).toFixed(1) : '0.0';
  const offerRate = totalApps > 0 ? ((offersCount / totalApps) * 100).toFixed(1) : '0.0';

  const defaultFunnel: Record<string, number> = {
    Draft: 0,
    Submitted: 0,
    'Under Review': 0,
    Interview: interviewsCount,
    Offer: offersCount,
  };
  const funnel = data?.funnel || defaultFunnel;

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Analytics & Search Insights"
        subtitle="Performance funnel, match distribution, and in-demand skills intelligence"
      />

      <div className="p-8 space-y-8 max-w-7xl w-full mx-auto">
        {/* KPI Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
            <div className="text-xs font-semibold text-slate-500 uppercase">Interview Conversion Rate</div>
            <div className="text-3xl font-extrabold text-amber-600 mt-2">{interviewRate}%</div>
            <p className="text-xs text-slate-400 mt-1">
              {interviewsCount} interview{interviewsCount === 1 ? '' : 's'} from {totalApps} tracked application{totalApps === 1 ? '' : 's'}
            </p>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
            <div className="text-xs font-semibold text-slate-500 uppercase">Offer Conversion Rate</div>
            <div className="text-3xl font-extrabold text-emerald-600 mt-2">{offerRate}%</div>
            <p className="text-xs text-slate-400 mt-1">
              {offersCount} offer{offersCount === 1 ? '' : 's'} received
            </p>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
            <div className="text-xs font-semibold text-slate-500 uppercase">Average High-Fit Match</div>
            <div className="text-3xl font-extrabold text-sky-600 mt-2">
              {data?.top_recommendations && data.top_recommendations.length > 0
                ? `${(
                    data.top_recommendations.reduce((acc, r) => acc + (r.overall_score || 0), 0) /
                    data.top_recommendations.length
                  ).toFixed(1)}%`
                : '0.0%'}
            </div>
            <p className="text-xs text-slate-400 mt-1">Across top recommended opportunities</p>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Top In-Demand Skills */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-sky-500" />
              Top Skills in Active Target Market
            </h3>

            <div className="space-y-3">
              {topSkills.length > 0 ? (
                topSkills.map((item, idx) => {
                  const maxVal = Math.max(...topSkills.map((s) => s.count), 1);
                  const pct = (item.count / maxVal) * 100;
                  return (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between text-xs font-semibold text-slate-700">
                        <span>{item.skill}</span>
                        <span className="text-slate-500">{item.count} postings</span>
                      </div>
                      <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                        <div
                          className="bg-sky-500 h-full rounded-full transition-all"
                          style={{ width: `${pct}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-xs text-slate-400 py-4 text-center">No skills data available yet.</p>
              )}
            </div>
          </div>

          {/* Full Pipeline Funnel */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-indigo-500" />
              Application Funnel Stages
            </h3>

            <div className="space-y-3">
              {Object.entries(funnel).map(([stage, count]) => (
                <div key={stage} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold text-slate-700">
                    <span>{stage}</span>
                    <span className="font-bold text-slate-900">{count}</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                    <div
                      className="bg-indigo-600 h-full rounded-full transition-all"
                      style={{ width: `${totalApps > 0 ? Math.min(100, (count / totalApps) * 100) : count > 0 ? 100 : 0}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
