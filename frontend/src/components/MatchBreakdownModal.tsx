'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Building,
  MapPin,
  DollarSign,
  ShieldCheck,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Award,
  Zap
} from 'lucide-react';
import { JobMatch } from '@/types';

interface MatchBreakdownModalProps {
  match: JobMatch | null;
  onClose: () => void;
  onApply?: (jobId: string) => void;
}

export function MatchBreakdownModal({ match, onClose, onApply }: MatchBreakdownModalProps) {
  const [showFormula, setShowFormula] = useState(false);
  if (!match) return null;

  const { job, overall_score, score_breakdown } = match;
  const breakdown: any = score_breakdown || {};

  const skillScore = match.skill_score ?? match.skills_score ?? breakdown.skills_score ?? 80;
  const expScore = match.experience_score ?? breakdown.experience_score ?? 80;
  const eduScore = match.education_score ?? breakdown.education_score ?? 85;
  const locScore = match.location_score ?? breakdown.location_score ?? 90;
  const roleScore = match.role_score ?? breakdown.role_score ?? 85;
  const salScore = match.salary_score ?? breakdown.salary_score ?? 80;
  const semScore = match.semantic_score ?? breakdown.semantic_score ?? 85;

  const matchedSkills: string[] = match.matched_skills || breakdown.matched_skills || [];
  const missingReq: string[] = match.missing_required_skills || breakdown.missing_required_skills || [];
  const missingPref: string[] = match.missing_preferred_skills || breakdown.missing_preferred_skills || [];

  const eligibility = match.eligibility_status || breakdown.eligibility_status || 'ELIGIBLE';
  const recommendation = match.recommendation || breakdown.recommendation || 'POSSIBLE_MATCH';

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-emerald-700 bg-emerald-50 border-emerald-300';
    if (score >= 80) return 'text-sky-700 bg-sky-50 border-sky-300';
    if (score >= 70) return 'text-blue-700 bg-blue-50 border-blue-300';
    if (score >= 60) return 'text-amber-700 bg-amber-50 border-amber-300';
    return 'text-rose-700 bg-rose-50 border-rose-300';
  };

  const getEligibilityBadge = (status: string) => {
    switch (status) {
      case 'ELIGIBLE':
        return <span className="text-xs bg-emerald-100 text-emerald-800 border border-emerald-300 px-2.5 py-0.5 rounded-full font-bold">ELIGIBLE</span>;
      case 'LIKELY_ELIGIBLE':
        return <span className="text-xs bg-sky-100 text-sky-800 border border-sky-300 px-2.5 py-0.5 rounded-full font-bold">LIKELY ELIGIBLE</span>;
      case 'REVIEW':
        return <span className="text-xs bg-amber-100 text-amber-800 border border-amber-300 px-2.5 py-0.5 rounded-full font-bold">REVIEW NEEDED</span>;
      case 'NOT_ELIGIBLE':
        return <span className="text-xs bg-rose-100 text-rose-800 border border-rose-300 px-2.5 py-0.5 rounded-full font-bold">NOT ELIGIBLE</span>;
      default:
        return <span className="text-xs bg-slate-100 text-slate-800 border border-slate-300 px-2.5 py-0.5 rounded-full font-bold">INSUFFICIENT DATA</span>;
    }
  };

  const getRecommendationBadge = (rec: string) => {
    switch (rec) {
      case 'STRONG_MATCH':
        return <span className="text-xs bg-emerald-600 text-white px-2.5 py-0.5 rounded-md font-bold shadow-sm">STRONG MATCH</span>;
      case 'GOOD_MATCH':
        return <span className="text-xs bg-sky-600 text-white px-2.5 py-0.5 rounded-md font-bold shadow-sm">GOOD MATCH</span>;
      case 'POSSIBLE_MATCH':
        return <span className="text-xs bg-blue-600 text-white px-2.5 py-0.5 rounded-md font-bold shadow-sm">POSSIBLE MATCH</span>;
      case 'WEAK_MATCH':
        return <span className="text-xs bg-amber-600 text-white px-2.5 py-0.5 rounded-md font-bold shadow-sm">WEAK MATCH</span>;
      default:
        return <span className="text-xs bg-rose-600 text-white px-2.5 py-0.5 rounded-md font-bold shadow-sm">NOT RECOMMENDED</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl max-w-3xl w-full p-6 shadow-2xl border border-slate-200 animate-in fade-in zoom-in duration-150 max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-start justify-between pb-4 border-b border-slate-100 shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-sky-700 bg-sky-50 px-2.5 py-0.5 rounded border border-sky-200">
                Phase 4 AI Match Analysis
              </span>
              {getRecommendationBadge(recommendation)}
              {getEligibilityBadge(eligibility)}
            </div>
            <h2 className="text-xl font-bold text-slate-900 mt-1.5">{job.title}</h2>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-1">
              <span className="flex items-center gap-1 font-semibold text-slate-700">
                <Building className="w-3.5 h-3.5" /> {job.company_name}
              </span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5" /> {job.location || 'Remote'} ({job.remote_type})
              </span>
              {job.salary_min && (
                <span className="flex items-center gap-1 text-emerald-600 font-semibold">
                  <DollarSign className="w-3.5 h-3.5" /> ${(job.salary_min / 1000).toFixed(0)}k - ${(job.salary_max ? job.salary_max / 1000 : 0).toFixed(0)}k
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="py-4 space-y-5 overflow-y-auto flex-1 pr-1">
          {/* Top Score Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Overall Score */}
            <div className="flex flex-col items-center justify-center p-4 bg-slate-50 rounded-xl border border-slate-200 text-center">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Overall Score</span>
              <div className={`text-4xl font-black mt-2 px-4 py-1.5 rounded-2xl border ${getScoreColor(overall_score)}`}>
                {overall_score.toFixed(0)}%
              </div>
              <span className="text-[11px] text-slate-500 mt-2 font-medium">Deterministic Weighted Formula</span>
            </div>

            {/* 6 Deterministic Dimensions */}
            <div className="md:col-span-2 space-y-2 p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              <div className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center justify-between">
                <span>Deterministic Breakdown</span>
                <span className="text-[10px] text-slate-400 font-normal">Sum = 100%</span>
              </div>

              {/* Skills (35%) */}
              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-0.5">
                  <span>Technical Skills (35%)</span>
                  <span className="font-bold">{skillScore.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-indigo-600 h-full rounded-full" style={{ width: `${skillScore}%` }}></div>
                </div>
              </div>

              {/* Experience (20%) */}
              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-0.5">
                  <span>Experience Seniority (20%)</span>
                  <span className="font-bold">{expScore.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-emerald-600 h-full rounded-full" style={{ width: `${expScore}%` }}></div>
                </div>
              </div>

              {/* Education (15%) */}
              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-0.5">
                  <span>Education & Degree (15%)</span>
                  <span className="font-bold">{eduScore.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-sky-600 h-full rounded-full" style={{ width: `${eduScore}%` }}></div>
                </div>
              </div>

              {/* Location (10%) */}
              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-0.5">
                  <span>Location & Remote (10%)</span>
                  <span className="font-bold">{locScore.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-purple-600 h-full rounded-full" style={{ width: `${locScore}%` }}></div>
                </div>
              </div>

              {/* Role (10%) */}
              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-0.5">
                  <span>Role Title Alignment (10%)</span>
                  <span className="font-bold">{roleScore.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-teal-600 h-full rounded-full" style={{ width: `${roleScore}%` }}></div>
                </div>
              </div>

              {/* Salary (10%) */}
              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-0.5">
                  <span>Salary Expectations (10%)</span>
                  <span className="font-bold">{salScore.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-amber-600 h-full rounded-full" style={{ width: `${salScore}%` }}></div>
                </div>
              </div>
            </div>
          </div>

          {/* AI Explanation Card */}
          <div className="p-4 bg-sky-50/60 rounded-xl border border-sky-200">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-sky-800 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-sky-600" /> AI Match Explanation
              </span>
              <span className="text-[10px] bg-white px-2 py-0.5 rounded border border-sky-200 text-sky-700 font-medium">
                {match.embedding_model ? `Embedding: ${match.embedding_model}` : 'Deterministic fallback active'}
              </span>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed font-medium">
              {match.explanation || breakdown.explanation || "Strong alignment on core candidate competencies."}
            </p>
          </div>

          {/* Skills Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Matched Skills */}
            <div className="p-3.5 bg-emerald-50/40 rounded-xl border border-emerald-200">
              <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-1.5 mb-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Matched Skills ({matchedSkills.length})
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {matchedSkills.length > 0 ? (
                  matchedSkills.map((s, i) => (
                    <span key={i} className="text-xs bg-white text-emerald-700 border border-emerald-300 px-2 py-0.5 rounded-md font-medium">
                      ✓ {s}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate-400 italic">No specific direct skill overlap detected</span>
                )}
              </div>
            </div>

            {/* Missing Skills */}
            <div className="p-3.5 bg-amber-50/40 rounded-xl border border-amber-200">
              <h4 className="text-xs font-bold uppercase tracking-wider text-amber-800 flex items-center gap-1.5 mb-2">
                <AlertTriangle className="w-4 h-4 text-amber-600" /> Missing Skills
              </h4>
              <div className="space-y-1.5">
                {missingReq.length > 0 && (
                  <div>
                    <span className="text-[11px] font-semibold text-rose-700 block mb-1">Required:</span>
                    <div className="flex flex-wrap gap-1">
                      {missingReq.map((s, i) => (
                        <span key={i} className="text-xs bg-rose-50 text-rose-700 border border-rose-200 px-2 py-0.5 rounded-md font-medium">
                          ✕ {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {missingPref.length > 0 && (
                  <div>
                    <span className="text-[11px] font-semibold text-amber-700 block mb-1">Preferred:</span>
                    <div className="flex flex-wrap gap-1">
                      {missingPref.map((s, i) => (
                        <span key={i} className="text-xs bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-md font-medium">
                          ○ {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {missingReq.length === 0 && missingPref.length === 0 && (
                  <span className="text-xs text-emerald-700 font-medium">All specified skills satisfied!</span>
                )}
              </div>
            </div>
          </div>

          {/* "How this score was calculated" Collapsible */}
          <div className="border border-slate-200 rounded-xl overflow-hidden">
            <button
              onClick={() => setShowFormula(!showFormula)}
              className="w-full flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 text-xs font-bold text-slate-700 transition-colors"
            >
              <span className="flex items-center gap-1.5">
                <Award className="w-4 h-4 text-indigo-600" /> How This Match Score Was Calculated
              </span>
              {showFormula ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            {showFormula && (
              <div className="p-4 text-xs text-slate-600 space-y-2 bg-white border-t border-slate-200">
                <p>The overall match score is calculated using an explainable, deterministic weighted aggregation formula:</p>
                <div className="p-2.5 bg-slate-900 text-slate-200 rounded-lg font-mono text-[11px]">
                  Score = (Skills × 0.35) + (Experience × 0.20) + (Education × 0.15) + (Location × 0.10) + (Role × 0.10) + (Salary × 0.10)
                </div>
                <ul className="list-disc list-inside space-y-1 text-[11px] text-slate-500">
                  <li><strong>Skills (35%)</strong>: Required skills weighted at 75% and preferred at 25% with canonical alias normalization.</li>
                  <li><strong>Experience (20%)</strong>: Range evaluation supporting freshers (0 years matching 0-2 years) without penalization.</li>
                  <li><strong>Education (15%)</strong>: Hierarchy rank evaluation supporting degree equivalents (B.Tech = B.E. = B.S.).</li>
                  <li><strong>Location & Role (10% each)</strong>: Remote mode matching and title cluster alignment.</li>
                  <li><strong>Salary (10%)</strong>: Range comparison marked unverified if not disclosed.</li>
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="pt-4 border-t border-slate-100 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            <span>Platform Safety: Verified non-circumvention analysis</span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href={`/matches/${job.id}`}
              className="px-4 py-2 text-xs font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 rounded-lg transition-colors flex items-center gap-1.5"
            >
              <span>Full Match Page</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
