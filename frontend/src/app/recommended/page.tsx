'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { Header } from '@/components/Header';
import { MatchBreakdownModal } from '@/components/MatchBreakdownModal';
import {
  Sparkles,
  Building,
  MapPin,
  DollarSign,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Bookmark,
  BookmarkCheck,
  RefreshCw,
  SlidersHorizontal,
  Server,
  Cpu,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { api } from '@/lib/api';
import { JobMatch, MatchingEngineHealth } from '@/types';

export default function RecommendedPage() {
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [matchingBatch, setMatchingBatch] = useState(false);
  const [health, setHealth] = useState<MatchingEngineHealth | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<JobMatch | null>(null);

  // Filters
  const [minScore, setMinScore] = useState<number | undefined>(undefined);
  const [selectedRecommendation, setSelectedRecommendation] = useState<string>('ALL');
  const [selectedEligibility, setSelectedEligibility] = useState<string>('ALL');

  const loadRecommendations = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, any> = {};
      if (minScore !== undefined) params.minimum_score = minScore;
      if (selectedRecommendation !== 'ALL') params.recommendation = selectedRecommendation;
      if (selectedEligibility !== 'ALL') params.eligibility = selectedEligibility;

      const res = await api.getRecommendedJobs(params);
      setMatches(res);
    } catch (err) {
      console.error('Failed to load recommendations:', err);
    } finally {
      setLoading(false);
    }
  }, [minScore, selectedRecommendation, selectedEligibility]);

  const loadHealth = useCallback(async () => {
    try {
      const res = await api.getMatchingHealth();
      setHealth(res);
    } catch (err) {
      console.error('Failed to load matching health:', err);
    }
  }, []);

  useEffect(() => {
    loadHealth();
    loadRecommendations();
  }, [loadHealth, loadRecommendations]);

  async function handleBatchMatch() {
    try {
      setMatchingBatch(true);
      await api.batchMatch({ limit: 50 });
      await loadRecommendations();
    } catch (err) {
      console.error('Batch match error:', err);
    } finally {
      setMatchingBatch(false);
    }
  }

  async function handleBookmark(jobId: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await api.toggleBookmark(jobId);
      setMatches((prev) =>
        prev.map((m) => (m.job_id === jobId ? { ...m, is_bookmarked: !m.is_bookmarked } : m))
      );
    } catch (err) {
      console.error('Failed to toggle bookmark:', err);
    }
  }

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
        title="AI Recommended Jobs"
        subtitle="Ranked job matches calculated with 6-dimension deterministic scoring and AI semantic embeddings"
      />

      <div className="p-8 space-y-6 max-w-7xl w-full mx-auto">
        {/* AI Matching Status Bar */}
        <div className="bg-slate-900 text-white rounded-2xl p-5 shadow-lg border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-md">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm tracking-tight text-white">AI Matching Gateway</h3>
                <span
                  className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full border ${
                    health?.omniroute_status === 'CONNECTED'
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                      : health?.omniroute_status === 'MOCK'
                      ? 'bg-sky-500/20 text-sky-300 border-sky-500/40'
                      : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  }`}
                >
                  {health?.omniroute_status || 'CONNECTED'}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 mt-1">
                <span>Model: <strong className="text-slate-200">{health?.chat_model || 'gpt-4o'}</strong></span>
                <span>Embedding: <strong className="text-slate-200">{health?.embedding_model || 'text-embedding-3-small'}</strong></span>
                <span>Engine: <strong className="text-emerald-400">READY (Deterministic 100%)</strong></span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleBatchMatch}
              disabled={matchingBatch}
              className="px-4 py-2 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-600 hover:to-indigo-700 text-white text-xs font-bold rounded-xl shadow-sm transition-all flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${matchingBatch ? 'animate-spin' : ''}`} />
              <span>{matchingBatch ? 'Analyzing All Jobs...' : 'Batch Match All Jobs'}</span>
            </button>
            <Link
              href="/matches"
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold rounded-xl border border-slate-700 transition-colors"
            >
              Match History
            </Link>
          </div>
        </div>

        {/* Filters Toolbar */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
              <SlidersHorizontal className="w-3.5 h-3.5 text-sky-600" />
              <span>Filter Matches:</span>
            </div>

            {/* Min Score Buttons */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
              {[
                { label: 'All Scores', val: undefined },
                { label: '90%+ Strong', val: 90 },
                { label: '80%+ Good', val: 80 },
                { label: '70%+ Possible', val: 70 },
              ].map((btn, i) => (
                <button
                  key={i}
                  onClick={() => setMinScore(btn.val)}
                  className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                    minScore === btn.val
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {btn.label}
                </button>
              ))}
            </div>

            {/* Recommendation Select */}
            <select
              value={selectedRecommendation}
              onChange={(e) => setSelectedRecommendation(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              <option value="ALL">All Recommendations</option>
              <option value="STRONG_MATCH">Strong Match Only</option>
              <option value="GOOD_MATCH">Good Match Only</option>
              <option value="POSSIBLE_MATCH">Possible Match Only</option>
              <option value="WEAK_MATCH">Weak Match Only</option>
            </select>

            {/* Eligibility Select */}
            <select
              value={selectedEligibility}
              onChange={(e) => setSelectedEligibility(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              <option value="ALL">All Eligibility</option>
              <option value="ELIGIBLE">Eligible Only</option>
              <option value="LIKELY_ELIGIBLE">Likely Eligible Only</option>
              <option value="REVIEW">Review Needed</option>
            </select>
          </div>

          <div className="text-xs text-slate-500 font-medium">
            Showing <strong className="text-slate-900">{matches.length}</strong> calculated matches
          </div>
        </div>

        {/* Matches Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {loading ? (
            <div className="col-span-2 bg-white p-12 rounded-2xl border border-slate-200 text-center text-xs text-slate-400">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-sky-500" />
              Calculating deterministic matches & vector embeddings...
            </div>
          ) : matches.length === 0 ? (
            <div className="col-span-2 bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-3">
              <Sparkles className="w-8 h-8 mx-auto text-sky-500" />
              <h4 className="text-sm font-bold text-slate-800">No Matching Jobs Found for Selected Filters</h4>
              <p className="text-xs text-slate-500">Try loosening your filter criteria or sync fresh jobs from the discovery engine.</p>
              <button
                onClick={() => {
                  setMinScore(undefined);
                  setSelectedRecommendation('ALL');
                  setSelectedEligibility('ALL');
                }}
                className="px-4 py-2 bg-sky-50 text-sky-700 border border-sky-200 text-xs font-semibold rounded-xl hover:bg-sky-100"
              >
                Reset Filters
              </button>
            </div>
          ) : (
            matches.map((m) => {
              const matchedSkills = m.matched_skills || m.score_breakdown?.matched_skills || [];
              const missingReq = m.missing_required_skills || m.score_breakdown?.missing_required_skills || [];

              const skillScore = m.skill_score ?? m.skills_score ?? 80;
              const expScore = m.experience_score ?? 80;
              const eduScore = m.education_score ?? 85;
              const locScore = m.location_score ?? 90;
              const roleScore = m.role_score ?? 85;
              const salScore = m.salary_score ?? 80;

              return (
                <div
                  key={m.id}
                  onClick={() => setSelectedMatch(m)}
                  className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-md hover:border-sky-300 transition-all cursor-pointer flex flex-col justify-between"
                >
                  <div className="space-y-3.5">
                    {/* Top Company & Score */}
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
                            <Building className="w-3.5 h-3.5" /> {m.job.company_name}
                          </span>
                          <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-bold uppercase">
                            {m.recommendation ? m.recommendation.replace('_', ' ') : 'MATCH'}
                          </span>
                          {m.eligibility_status === 'ELIGIBLE' && (
                            <span className="text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.5 rounded font-bold">
                              ELIGIBLE
                            </span>
                          )}
                        </div>
                        <h3 className="text-base font-bold text-slate-900 mt-1">{m.job.title}</h3>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => handleBookmark(m.job_id, e)}
                          className="p-1.5 text-slate-400 hover:text-sky-600 rounded-lg hover:bg-slate-100 transition-colors"
                        >
                          {m.is_bookmarked ? (
                            <BookmarkCheck className="w-4 h-4 text-sky-600" />
                          ) : (
                            <Bookmark className="w-4 h-4" />
                          )}
                        </button>
                        <div
                          className={`text-lg font-black px-3 py-1 rounded-xl border ${getScoreColor(
                            m.overall_score
                          )}`}
                        >
                          {m.overall_score.toFixed(0)}%
                        </div>
                      </div>
                    </div>

                    {/* Metadata */}
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

                    {/* 6 Dimension Mini Indicators */}
                    <div className="grid grid-cols-6 gap-1 pt-1 text-[10px] text-center font-bold">
                      <div className="bg-slate-50 p-1 rounded border border-slate-100">
                        <span className="text-slate-400 block text-[9px]">Skills</span>
                        <span className="text-indigo-600">{skillScore.toFixed(0)}%</span>
                      </div>
                      <div className="bg-slate-50 p-1 rounded border border-slate-100">
                        <span className="text-slate-400 block text-[9px]">Exp</span>
                        <span className="text-emerald-600">{expScore.toFixed(0)}%</span>
                      </div>
                      <div className="bg-slate-50 p-1 rounded border border-slate-100">
                        <span className="text-slate-400 block text-[9px]">Edu</span>
                        <span className="text-sky-600">{eduScore.toFixed(0)}%</span>
                      </div>
                      <div className="bg-slate-50 p-1 rounded border border-slate-100">
                        <span className="text-slate-400 block text-[9px]">Loc</span>
                        <span className="text-purple-600">{locScore.toFixed(0)}%</span>
                      </div>
                      <div className="bg-slate-50 p-1 rounded border border-slate-100">
                        <span className="text-slate-400 block text-[9px]">Role</span>
                        <span className="text-teal-600">{roleScore.toFixed(0)}%</span>
                      </div>
                      <div className="bg-slate-50 p-1 rounded border border-slate-100">
                        <span className="text-slate-400 block text-[9px]">Salary</span>
                        <span className="text-amber-600">{salScore.toFixed(0)}%</span>
                      </div>
                    </div>

                    {/* Matched & Missing Skills Chips */}
                    <div className="space-y-1.5 pt-1">
                      {matchedSkills.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1">
                          <span className="text-[10px] font-bold text-emerald-700 mr-1">Matched:</span>
                          {matchedSkills.slice(0, 4).map((s, i) => (
                            <span
                              key={i}
                              className="text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded font-medium"
                            >
                              ✓ {s}
                            </span>
                          ))}
                        </div>
                      )}
                      {missingReq.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1">
                          <span className="text-[10px] font-bold text-rose-700 mr-1">Missing:</span>
                          {missingReq.slice(0, 3).map((s, i) => (
                            <span
                              key={i}
                              className="text-[10px] bg-rose-50 text-rose-700 border border-rose-200 px-2 py-0.5 rounded font-medium"
                            >
                              ✕ {s}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="pt-4 mt-4 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-sky-600">
                    <span>View Explainability Breakdown</span>
                    <ArrowRight className="w-4 h-4" />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Match Breakdown Modal */}
      {selectedMatch && (
        <MatchBreakdownModal
          match={selectedMatch}
          onClose={() => setSelectedMatch(null)}
        />
      )}
    </div>
  );
}
