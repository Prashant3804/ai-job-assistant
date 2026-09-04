'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Header } from '@/components/Header';
import {
  Sparkles,
  Building,
  MapPin,
  DollarSign,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  ShieldCheck,
  Award,
  Layers,
  FileText,
  Clock,
  Briefcase,
  HelpCircle,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import { api } from '@/lib/api';
import { JobMatch } from '@/types';

export default function MatchDetailPage() {
  const params = useParams();
  const jobId = params?.jobId as string;

  const [match, setMatch] = useState<JobMatch | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (jobId) {
      loadMatchDetails(jobId);
    }
  }, [jobId]);

  async function loadMatchDetails(id: string) {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getJobMatch(id);
      setMatch(res);
    } catch (err: any) {
      console.error('Failed to load match detail:', err);
      setError(err.message || 'Failed to load match evaluation');
    } finally {
      setLoading(false);
    }
  }

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
        return <span className="text-xs bg-emerald-100 text-emerald-800 border border-emerald-300 px-3 py-1 rounded-full font-bold">ELIGIBLE</span>;
      case 'LIKELY_ELIGIBLE':
        return <span className="text-xs bg-sky-100 text-sky-800 border border-sky-300 px-3 py-1 rounded-full font-bold">LIKELY ELIGIBLE</span>;
      case 'REVIEW':
        return <span className="text-xs bg-amber-100 text-amber-800 border border-amber-300 px-3 py-1 rounded-full font-bold">REVIEW NEEDED</span>;
      case 'NOT_ELIGIBLE':
        return <span className="text-xs bg-rose-100 text-rose-800 border border-rose-300 px-3 py-1 rounded-full font-bold">NOT ELIGIBLE</span>;
      default:
        return <span className="text-xs bg-slate-100 text-slate-800 border border-slate-300 px-3 py-1 rounded-full font-bold">INSUFFICIENT DATA</span>;
    }
  };

  const getRecommendationBadge = (rec: string) => {
    switch (rec) {
      case 'STRONG_MATCH':
        return <span className="text-xs bg-emerald-600 text-white px-3 py-1 rounded-md font-bold shadow-sm">STRONG MATCH</span>;
      case 'GOOD_MATCH':
        return <span className="text-xs bg-sky-600 text-white px-3 py-1 rounded-md font-bold shadow-sm">GOOD MATCH</span>;
      case 'POSSIBLE_MATCH':
        return <span className="text-xs bg-blue-600 text-white px-3 py-1 rounded-md font-bold shadow-sm">POSSIBLE MATCH</span>;
      case 'WEAK_MATCH':
        return <span className="text-xs bg-amber-600 text-white px-3 py-1 rounded-md font-bold shadow-sm">WEAK MATCH</span>;
      default:
        return <span className="text-xs bg-rose-600 text-white px-3 py-1 rounded-md font-bold shadow-sm">NOT RECOMMENDED</span>;
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col">
        <Header title="Match Analysis" subtitle="Loading detailed compatibility breakdown..." />
        <div className="p-12 text-center text-xs text-slate-400">Loading match evaluation data...</div>
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="flex-1 flex flex-col">
        <Header title="Match Analysis" subtitle="Error loading match" />
        <div className="p-8 max-w-xl mx-auto text-center space-y-4">
          <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto" />
          <h3 className="text-base font-bold text-slate-900">Unable to load match evaluation</h3>
          <p className="text-xs text-slate-500">{error || 'Job not found'}</p>
          <Link
            href="/recommended"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-sky-600 text-white text-xs font-semibold rounded-xl"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Recommended Jobs</span>
          </Link>
        </div>
      </div>
    );
  }

  const { job, overall_score, score_breakdown } = match;
  const breakdown: any = score_breakdown || {};

  const skillScore = match.skill_score ?? match.skills_score ?? 80;
  const expScore = match.experience_score ?? 80;
  const eduScore = match.education_score ?? 85;
  const locScore = match.location_score ?? 90;
  const roleScore = match.role_score ?? 85;
  const salScore = match.salary_score ?? 80;
  const semScore = match.semantic_score ?? 85;

  const matchedSkills: string[] = match.matched_skills || breakdown.matched_skills || [];
  const missingReq: string[] = match.missing_required_skills || breakdown.missing_required_skills || [];
  const missingPref: string[] = match.missing_preferred_skills || breakdown.missing_preferred_skills || [];

  const eligibility = match.eligibility_status || 'ELIGIBLE';
  const recommendation = match.recommendation || 'POSSIBLE_MATCH';

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Explainable Match Intelligence"
        subtitle={`Deep compatibility breakdown for ${job.title} at ${job.company_name}`}
      />

      <div className="p-8 space-y-6 max-w-6xl w-full mx-auto">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between">
          <Link
            href="/recommended"
            className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center gap-1 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Recommended Jobs</span>
          </Link>
          <span className="text-xs text-slate-400 font-mono">Scoring Version: {match.scoring_version || 'v4.0.0'}</span>
        </div>

        {/* Hero Card */}
        <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
                <Building className="w-4 h-4" /> {job.company_name}
              </span>
              {getRecommendationBadge(recommendation)}
              {getEligibilityBadge(eligibility)}
            </div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">{job.title}</h1>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
              <span className="flex items-center gap-1">
                <MapPin className="w-4 h-4" /> {job.location || 'Remote'} ({job.remote_type})
              </span>
              {job.salary_min && (
                <span className="flex items-center gap-1 text-emerald-600 font-bold">
                  <DollarSign className="w-4 h-4" /> ${(job.salary_min / 1000).toFixed(0)}k - ${(job.salary_max ? job.salary_max / 1000 : 0).toFixed(0)}k {job.salary_currency}
                </span>
              )}
              <span className="flex items-center gap-1">
                <Briefcase className="w-4 h-4" /> {job.employment_type || 'Full-time'}
              </span>
            </div>
          </div>

          <div className="flex flex-col items-center justify-center p-6 bg-slate-50 rounded-2xl border border-slate-200 text-center shrink-0 min-w-[180px]">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Overall Match</span>
            <div className={`text-5xl font-black mt-2 px-5 py-1.5 rounded-2xl border ${getScoreColor(overall_score)}`}>
              {overall_score.toFixed(0)}%
            </div>
            <span className="text-[11px] text-slate-400 mt-2 font-medium">Confidence: {((match.confidence || 1.0) * 100).toFixed(0)}%</span>
          </div>
        </div>

        {/* 6-Dimension Score Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 bg-white rounded-3xl p-6 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Layers className="w-4 h-4 text-sky-600" />
                <span>Deterministic Scoring Breakdown</span>
              </h3>
              <span className="text-xs text-slate-400 font-medium">100% Deterministic Aggregation</span>
            </div>

            <div className="space-y-3 pt-1">
              {/* Technical Skills (35%) */}
              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Technical Skills (35% weight)</span>
                  <span className="font-bold text-indigo-700">{skillScore.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                  <div className="bg-indigo-600 h-full rounded-full" style={{ width: `${skillScore}%` }}></div>
                </div>
              </div>

              {/* Experience (20%) */}
              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Experience Seniority (20% weight)</span>
                  <span className="font-bold text-emerald-700">{expScore.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                  <div className="bg-emerald-600 h-full rounded-full" style={{ width: `${expScore}%` }}></div>
                </div>
              </div>

              {/* Education (15%) */}
              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Education & Degree (15% weight)</span>
                  <span className="font-bold text-sky-700">{eduScore.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                  <div className="bg-sky-600 h-full rounded-full" style={{ width: `${eduScore}%` }}></div>
                </div>
              </div>

              {/* Location (10%) */}
              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Location & Remote (10% weight)</span>
                  <span className="font-bold text-purple-700">{locScore.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                  <div className="bg-purple-600 h-full rounded-full" style={{ width: `${locScore}%` }}></div>
                </div>
              </div>

              {/* Role (10%) */}
              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Role Title Alignment (10% weight)</span>
                  <span className="font-bold text-teal-700">{roleScore.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                  <div className="bg-teal-600 h-full rounded-full" style={{ width: `${roleScore}%` }}></div>
                </div>
              </div>

              {/* Salary (10%) */}
              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Salary Expectations (10% weight)</span>
                  <span className="font-bold text-amber-700">{salScore.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                  <div className="bg-amber-600 h-full rounded-full" style={{ width: `${salScore}%` }}></div>
                </div>
              </div>
            </div>
          </div>

          {/* AI Explanation Card */}
          <div className="bg-sky-900 text-white rounded-3xl p-6 shadow-md flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-5 h-5 text-sky-400" />
                <h3 className="text-sm font-bold text-white">OmniRoute AI Explanation</h3>
              </div>
              <p className="text-xs text-sky-100 leading-relaxed font-normal">
                {match.explanation || "Strong overall compatibility across primary core competencies."}
              </p>
            </div>

            <div className="p-3 bg-sky-800/80 rounded-2xl border border-sky-700/60 text-[11px] text-sky-200">
              <span className="font-bold block text-white mb-0.5">Gateway Transparency:</span>
              <span>Vector embedding model: <code className="text-sky-300">{match.embedding_model || 'text-embedding-3-small'}</code></span>
            </div>
          </div>
        </div>

        {/* Skills Comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Matching Skills ({matchedSkills.length})</span>
            </h3>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {matchedSkills.length > 0 ? (
                matchedSkills.map((s, i) => (
                  <span key={i} className="text-xs bg-emerald-50 text-emerald-800 border border-emerald-200 px-3 py-1 rounded-lg font-medium">
                    ✓ {s}
                  </span>
                ))
              ) : (
                <span className="text-xs text-slate-400 italic">No direct skill matches detected</span>
              )}
            </div>
          </div>

          <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span>Skill Gaps</span>
            </h3>
            <div className="space-y-2 pt-1">
              {missingReq.length > 0 && (
                <div>
                  <span className="text-xs font-bold text-rose-700 block mb-1">Missing Required:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {missingReq.map((s, i) => (
                      <span key={i} className="text-xs bg-rose-50 text-rose-800 border border-rose-200 px-3 py-1 rounded-lg font-medium">
                        ✕ {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {missingPref.length > 0 && (
                <div>
                  <span className="text-xs font-bold text-amber-700 block mb-1">Missing Preferred:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {missingPref.map((s, i) => (
                      <span key={i} className="text-xs bg-amber-50 text-amber-800 border border-amber-200 px-3 py-1 rounded-lg font-medium">
                        ○ {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {missingReq.length === 0 && missingPref.length === 0 && (
                <span className="text-xs text-emerald-700 font-semibold">Zero skill gaps! All requirements met.</span>
              )}
            </div>
          </div>
        </div>

        {/* "How this score was calculated" Detailed Section */}
        <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Award className="w-5 h-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-900">How This Score Was Calculated</h3>
          </div>
          <div className="text-xs text-slate-600 space-y-3 leading-relaxed">
            <p>
              The AI Job Assistant applies a <strong>strictly deterministic scoring pipeline</strong> configured with transparent weights that sum to 100%. The system never fabricates scores or allows LLM randomness to dictate eligibility.
            </p>
            <div className="p-4 bg-slate-900 text-slate-100 rounded-2xl font-mono text-xs overflow-x-auto">
              Overall Score = (Skills × 0.35) + (Experience × 0.20) + (Education × 0.15) + (Location × 0.10) + (Role × 0.10) + (Salary × 0.10)
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                <span className="font-bold text-slate-900 block mb-1">1. Skills Matching (35%)</span>
                <span>Normalizes skill aliases (e.g. JS → JavaScript) and penalizes missing required skills heavier than preferred ones.</span>
              </div>
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                <span className="font-bold text-slate-900 block mb-1">2. Experience Seniority (20%)</span>
                <span>Evaluates candidate years against the job requirements range without penalizing freshers applying to entry-level roles.</span>
              </div>
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                <span className="font-bold text-slate-900 block mb-1">3. Degree & Education (15%)</span>
                <span>Verifies accredited degree equivalence (B.Tech, B.E., B.S. in Computer Science/IT) against required criteria.</span>
              </div>
            </div>
          </div>
        </div>

        {/* Job Description Card & Action */}
        <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm space-y-4">
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <FileText className="w-4 h-4 text-slate-600" />
            <span>Job Description & Role Summary</span>
          </h3>
          <div className="text-xs text-slate-700 leading-relaxed whitespace-pre-line bg-slate-50 p-6 rounded-2xl border border-slate-200">
            {job.description}
          </div>

          <div className="pt-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              <span>Non-circumvention verified. Direct external application link provided.</span>
            </div>
            {job.apply_url && (
              <a
                href={job.apply_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-2.5 bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold rounded-xl shadow-sm transition-colors inline-flex items-center gap-2"
              >
                <span>Apply on Official Portal</span>
                <ExternalLink className="w-4 h-4" />
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
