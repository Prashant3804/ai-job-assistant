'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Header } from '@/components/Header';
import { MatchBreakdownModal } from '@/components/MatchBreakdownModal';
import {
  BarChart3,
  Building,
  MapPin,
  DollarSign,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Bookmark,
  BookmarkCheck,
  RefreshCw,
  Search,
  Award,
  Sparkles
} from 'lucide-react';
import { api } from '@/lib/api';
import { JobMatch } from '@/types';

export default function MatchesHistoryPage() {
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMatch, setSelectedMatch] = useState<JobMatch | null>(null);

  useEffect(() => {
    loadMatchHistory();
  }, []);

  async function loadMatchHistory() {
    try {
      setLoading(true);
      const res = await api.getMatchHistory();
      setMatches(res);
    } catch (err) {
      console.error('Failed to load match history:', err);
    } finally {
      setLoading(false);
    }
  }

  const filteredMatches = matches.filter((m) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      m.job.title.toLowerCase().includes(q) ||
      m.job.company_name.toLowerCase().includes(q) ||
      (m.job.location && m.job.location.toLowerCase().includes(q))
    );
  });

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-emerald-700 bg-emerald-50 border-emerald-300';
    if (score >= 80) return 'text-sky-700 bg-sky-50 border-sky-300';
    if (score >= 70) return 'text-blue-700 bg-blue-50 border-blue-300';
    if (score >= 60) return 'text-amber-700 bg-amber-50 border-amber-300';
    return 'text-rose-700 bg-rose-50 border-rose-300';
  };

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Candidate Match History"
        subtitle="Chronological audit log of all candidate-job evaluations and explainability scores"
      />

      <div className="p-8 space-y-6 max-w-7xl w-full mx-auto">
        {/* Top bar with stats and search */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3 w-full md:w-auto flex-1 max-w-md">
            <div className="relative w-full">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search evaluated companies, titles, or locations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs text-slate-600">
            <span>Total Evaluated: <strong className="text-slate-900">{matches.length}</strong></span>
            <Link
              href="/recommended"
              className="px-3.5 py-1.5 bg-sky-50 text-sky-700 border border-sky-200 rounded-xl font-semibold hover:bg-sky-100 transition-colors flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5 text-sky-600" />
              <span>Recommended Jobs</span>
            </Link>
          </div>
        </div>

        {/* Matches List */}
        <div className="space-y-4">
          {loading ? (
            <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center text-xs text-slate-400">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-sky-500" />
              Loading match evaluation records...
            </div>
          ) : filteredMatches.length === 0 ? (
            <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-3">
              <BarChart3 className="w-8 h-8 mx-auto text-slate-400" />
              <h4 className="text-sm font-bold text-slate-800">No Match History Found</h4>
              <p className="text-xs text-slate-500">Run a discovery sync or evaluate jobs from the Find Jobs page to populate history.</p>
            </div>
          ) : (
            filteredMatches.map((m) => (
              <div
                key={m.id}
                className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hover:shadow-md hover:border-sky-300 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
                      <Building className="w-3.5 h-3.5" /> {m.job.company_name}
                    </span>
                    <span className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-bold uppercase">
                      {m.recommendation ? m.recommendation.replace('_', ' ') : 'MATCH'}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      Evaluated: {new Date(m.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-slate-900">
                    <Link href={`/matches/${m.job_id}`} className="hover:text-sky-600 transition-colors">
                      {m.job.title}
                    </Link>
                  </h3>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5" /> {m.job.location || 'Remote'} ({m.job.remote_type})
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
                    <div className={`text-xl font-black px-3 py-1 rounded-xl border ${getScoreColor(m.overall_score)}`}>
                      {m.overall_score.toFixed(0)}%
                    </div>
                    <span className="text-[10px] text-slate-400 block mt-0.5 font-medium">
                      {m.eligibility_status || 'ELIGIBLE'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setSelectedMatch(m)}
                      className="px-3 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold rounded-xl transition-colors"
                    >
                      Quick View
                    </button>
                    <Link
                      href={`/matches/${m.job_id}`}
                      className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold rounded-xl shadow-sm transition-colors flex items-center gap-1.5"
                    >
                      <span>Details</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {selectedMatch && (
        <MatchBreakdownModal
          match={selectedMatch}
          onClose={() => setSelectedMatch(null)}
        />
      )}
    </div>
  );
}
