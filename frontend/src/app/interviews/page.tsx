'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import {
  Calendar,
  Clock,
  Video,
  Building,
  Sparkles,
  CheckCircle2,
  BookOpen,
  ArrowRight,
  ShieldCheck,
  Plus,
  AlertTriangle,
  ExternalLink,
  MessageSquare,
  Copy,
  Check,
  Layers,
  HelpCircle,
  TrendingUp,
} from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';
import {
  InterviewSession,
  InterviewPrepBrief,
  FollowUpRecommendation,
  InterviewRoundType,
  InterviewStatus,
} from '@/types';

export default function InterviewsPage() {
  const [interviews, setInterviews] = useState<InterviewSession[]>([]);
  const [followUps, setFollowUps] = useState<FollowUpRecommendation[]>([]);
  const [selectedBrief, setSelectedBrief] = useState<InterviewPrepBrief | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGeneratingBrief, setIsGeneratingBrief] = useState(false);
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  // Prep brief generator modal state
  const [isBriefModalOpen, setIsBriefModalOpen] = useState(false);
  const [companyName, setCompanyName] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [roundType, setRoundType] = useState<InterviewRoundType>('TECHNICAL_SCREEN');
  const [jobDescription, setJobDescription] = useState('');

  // Schedule interview modal state
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false);
  const [schedTitle, setSchedTitle] = useState('');
  const [schedCompany, setSchedCompany] = useState('');
  const [schedRole, setSchedRole] = useState('');
  const [schedRound, setSchedRound] = useState<InterviewRoundType>('TECHNICAL_SCREEN');
  const [schedDate, setSchedDate] = useState('');
  const [schedDuration, setSchedDuration] = useState(45);
  const [schedMeetingUrl, setSchedMeetingUrl] = useState('');
  const [schedPlatform, setSchedPlatform] = useState('Zoom');

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setIsLoading(true);
    try {
      const [interviewsData, followUpsData] = await Promise.all([
        api.getInterviews().catch(() => []),
        api.getFollowUpRecommendations().catch(() => []),
      ]);
      setInterviews(interviewsData || []);
      setFollowUps(followUpsData || []);

      // If we have an interview, try to fetch its prep brief
      if (interviewsData && interviewsData.length > 0) {
        try {
          const brief = await api.getInterviewPrepBrief(interviewsData[0].id);
          setSelectedBrief(brief);
        } catch (_) {
          // No brief generated yet
        }
      }
    } catch (err) {
      console.error('Failed to load interview intelligence data:', err);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleGenerateBrief(e: React.FormEvent) {
    e.preventDefault();
    if (!companyName || !jobTitle) return;

    setIsGeneratingBrief(true);
    try {
      const brief = await api.generateInterviewPrepBrief({
        company_name: companyName,
        job_title: jobTitle,
        round_type: roundType,
        job_description: jobDescription || undefined,
      });
      setSelectedBrief(brief);
      setIsBriefModalOpen(false);
    } catch (err: any) {
      alert(`Failed to generate brief: ${err.message || err}`);
    } finally {
      setIsGeneratingBrief(false);
    }
  }

  async function handleScheduleInterview(e: React.FormEvent) {
    e.preventDefault();
    if (!schedCompany || !schedTitle || !schedDate) return;

    try {
      const created = await api.createInterview({
        title: schedTitle,
        company_name: schedCompany,
        job_title: schedRole || undefined,
        round_type: schedRound,
        scheduled_at: new Date(schedDate).toISOString(),
        duration_minutes: schedDuration,
        meeting_url: schedMeetingUrl || undefined,
        meeting_platform: schedPlatform,
      });
      setInterviews((prev) => [created, ...prev]);
      setIsScheduleModalOpen(false);

      // Auto-generate prep brief for new interview
      try {
        const brief = await api.generateInterviewPrepBrief({
          interview_id: created.id,
          company_name: created.company_name,
          job_title: created.job_title || 'Software Engineer',
          round_type: created.round_type,
        });
        setSelectedBrief(brief);
      } catch (_) {}
    } catch (err: any) {
      alert(`Failed to schedule interview: ${err.message || err}`);
    }
  }

  function handleCopy(text: string, section: string) {
    navigator.clipboard.writeText(text);
    setCopiedSection(section);
    setTimeout(() => setCopiedSection(null), 2000);
  }

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-900 text-slate-100">
      <Header
        title="Interviews & AI Preparation Intelligence"
        subtitle="Manage upcoming technical loops, generate tailored STAR briefing cheat sheets, and prevent recruiter ghosting."
      />

      <div className="p-8 space-y-8 max-w-7xl w-full mx-auto">
        {/* Top Control Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold px-3 py-1 rounded-full bg-sky-500/20 text-sky-400 border border-sky-500/30 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-sky-400" /> Human-in-the-Loop Enforced
            </span>
            <span className="text-xs font-semibold px-3 py-1 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-purple-400" /> OmniRoute AI Enabled
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsBriefModalOpen(true)}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-bold text-xs px-4 py-2.5 rounded-xl shadow-lg transition-all"
            >
              <Sparkles className="w-4 h-4" />
              <span>Generate Prep Brief</span>
            </button>
            <button
              onClick={() => setIsScheduleModalOpen(true)}
              className="inline-flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs px-4 py-2.5 rounded-xl border border-slate-700 transition-all"
            >
              <Plus className="w-4 h-4 text-sky-400" />
              <span>Record Interview</span>
            </button>
          </div>
        </div>

        {/* Scheduled Interviews & Active Round */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Scheduled Interviews List */}
          <div className="lg:col-span-2 space-y-4">
            <h2 className="text-base font-bold text-slate-200 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-sky-400" />
              Upcoming Interview Loops ({interviews.length})
            </h2>

            {interviews.length === 0 ? (
              <div className="bg-slate-800/40 border border-slate-800 rounded-2xl p-8 text-center space-y-3">
                <Calendar className="w-8 h-8 text-slate-600 mx-auto" />
                <p className="text-sm text-slate-400 font-medium">No scheduled interviews recorded yet.</p>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Sync your mailbox to automatically detect interview links, or manually add an upcoming round.
                </p>
                <button
                  onClick={() => setIsScheduleModalOpen(true)}
                  className="text-xs text-sky-400 hover:text-sky-300 font-bold underline"
                >
                  Record an Interview Now
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {interviews.map((intv) => (
                  <div
                    key={intv.id}
                    className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-6 transition-all shadow-md"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <span className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-bold px-2.5 py-0.5 rounded-full">
                            {intv.round_type.replace('_', ' ')}
                          </span>
                          <span className="text-xs font-semibold text-slate-300">{intv.company_name}</span>
                        </div>
                        <h3 className="text-base font-bold text-white tracking-tight">{intv.title}</h3>
                        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 pt-1">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5 text-emerald-400" />
                            {new Date(intv.scheduled_at).toLocaleString('en-US', {
                              weekday: 'short',
                              month: 'short',
                              day: 'numeric',
                              hour: 'numeric',
                              minute: '2-digit',
                            })}{' '}
                            ({intv.duration_minutes}m)
                          </span>
                          {intv.meeting_platform && (
                            <span className="flex items-center gap-1 text-purple-300">
                              <Video className="w-3.5 h-3.5" />
                              {intv.meeting_platform}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 self-start sm:self-center">
                        {intv.meeting_url && (
                          <a
                            href={intv.meeting_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 bg-sky-500 hover:bg-sky-400 text-slate-950 text-xs font-bold px-3.5 py-2 rounded-xl transition-all shadow-sm"
                          >
                            <Video className="w-3.5 h-3.5" />
                            <span>Join Call</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                        <button
                          onClick={async () => {
                            try {
                              const brief = await api.getInterviewPrepBrief(intv.id);
                              setSelectedBrief(brief);
                            } catch (_) {
                              // generate on demand
                              const brief = await api.generateInterviewPrepBrief({
                                interview_id: intv.id,
                                company_name: intv.company_name,
                                job_title: intv.job_title || 'Software Engineer',
                                round_type: intv.round_type,
                              });
                              setSelectedBrief(brief);
                            }
                          }}
                          className="inline-flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold px-3.5 py-2 rounded-xl border border-slate-700 transition-all"
                        >
                          <BookOpen className="w-3.5 h-3.5 text-sky-400" />
                          <span>View Brief</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Follow-up / Ghosting Detection Widget */}
          <div className="space-y-4">
            <h2 className="text-base font-bold text-slate-200 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-amber-400" />
              Follow-up & Stalled Pipelines ({followUps.length})
            </h2>

            {followUps.length === 0 ? (
              <div className="bg-slate-800/40 border border-slate-800 rounded-2xl p-6 text-center space-y-2">
                <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto" />
                <p className="text-xs text-slate-300 font-semibold">All pipelines healthy & active</p>
                <p className="text-[11px] text-slate-500">No communication stagnation or ghosting detected.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {followUps.map((fu, idx) => (
                  <div
                    key={idx}
                    className="bg-slate-800/60 border border-slate-800 hover:border-slate-700 rounded-2xl p-4 space-y-2.5 transition-all"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-xs text-slate-200 truncate">{fu.company_name}</span>
                      <span
                        className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                          fu.nudge_priority === 'HIGH'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : fu.nudge_priority === 'MEDIUM'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                        }`}
                      >
                        {fu.nudge_priority} NUDGE ({fu.days_inactive}d)
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-400 leading-snug">{fu.suggested_action}</p>

                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[10px] text-slate-500">{fu.job_title}</span>
                      <button
                        onClick={async () => {
                          try {
                            await api.generateResponseDraft({
                              company_name: fu.company_name,
                              job_title: fu.job_title,
                              intent: fu.recommended_intent,
                              tone: 'PROFESSIONAL',
                            });
                            alert('Follow-up draft pre-generated! Check your Communication Drafts or Mailbox.');
                          } catch (err: any) {
                            alert(`Failed to create draft: ${err.message || err}`);
                          }
                        }}
                        className="text-xs font-bold text-sky-400 hover:text-sky-300 flex items-center gap-1"
                      >
                        <span>Draft Follow-up</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Selected Interview Prep Brief Cheat-Sheet */}
        {selectedBrief && (
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 space-y-8 shadow-2xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
              <div>
                <div className="flex items-center gap-2">
                  <span className="bg-sky-500/20 text-sky-300 border border-sky-500/30 text-xs font-bold px-3 py-0.5 rounded-full">
                    AI Preparation Cheat Sheet
                  </span>
                  <span className="text-xs text-slate-400">{selectedBrief.company_name}</span>
                </div>
                <h2 className="text-2xl font-extrabold text-white mt-2">{selectedBrief.job_title} Briefing</h2>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleCopy(selectedBrief.cheat_sheet_markdown || '', 'markdown')}
                  className="inline-flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold px-4 py-2 rounded-xl border border-slate-700 transition-all"
                >
                  {copiedSection === 'markdown' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedSection === 'markdown' ? 'Copied Markdown' : 'Copy Cheat Sheet'}</span>
                </button>
              </div>
            </div>

            {/* Company & Role Intel */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-slate-800/40 border border-slate-800 rounded-2xl p-5 space-y-2">
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Building className="w-3.5 h-3.5 text-sky-400" /> Company Intelligence
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">{selectedBrief.company_overview}</p>
              </div>

              <div className="bg-slate-800/40 border border-slate-800 rounded-2xl p-5 space-y-2">
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-purple-400" /> Role Objectives
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">{selectedBrief.role_summary}</p>
              </div>
            </div>

            {/* Technical Focus Areas */}
            {selectedBrief.technical_focus_areas && selectedBrief.technical_focus_areas.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-sky-400" />
                  Key Technical Focus Areas
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                  {selectedBrief.technical_focus_areas.map((area, i) => (
                    <div key={i} className="p-3.5 bg-slate-800/60 border border-slate-800 rounded-xl text-xs text-slate-300 font-medium">
                      {area}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tailored STAR Stories */}
            {selectedBrief.star_stories && selectedBrief.star_stories.length > 0 && (
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  Tailored Candidate STAR Stories
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {selectedBrief.star_stories.map((story, i) => (
                    <div key={i} className="p-5 bg-slate-800/60 border border-slate-800 rounded-2xl space-y-2.5">
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-xs text-amber-300">{story.title}</h4>
                      </div>
                      <div className="space-y-1.5 text-xs text-slate-300 leading-relaxed">
                        <p><strong className="text-slate-400">Situation:</strong> {story.situation}</p>
                        <p><strong className="text-slate-400">Task:</strong> {story.task}</p>
                        <p><strong className="text-slate-400">Action:</strong> {story.action}</p>
                        <p><strong className="text-emerald-400">Result:</strong> {story.result}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Strategic Reverse Questions */}
            {selectedBrief.reverse_questions_to_ask && selectedBrief.reverse_questions_to_ask.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                  <HelpCircle className="w-4 h-4 text-indigo-400" />
                  High-Impact Questions to Ask Interviewers
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {selectedBrief.reverse_questions_to_ask.map((q, i) => (
                    <div key={i} className="p-3.5 bg-slate-800/40 border border-slate-800 rounded-xl text-xs text-slate-300 flex items-start gap-2">
                      <span className="text-sky-400 font-bold">{i + 1}.</span>
                      <span>{q}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modal: Generate Prep Brief */}
      {isBriefModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 max-w-lg w-full space-y-5 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-sky-400" />
              Generate AI Interview Prep Brief
            </h3>
            <form onSubmit={handleGenerateBrief} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Company Name</label>
                <input
                  type="text"
                  required
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g. Anthropic, Stripe, OpenAI"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Job Title</label>
                <input
                  type="text"
                  required
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  placeholder="e.g. Senior Backend Engineer"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Round Type</label>
                <select
                  value={roundType}
                  onChange={(e) => setRoundType(e.target.value as any)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-sky-500"
                >
                  <option value="TECHNICAL_SCREEN">Technical Screen</option>
                  <option value="SYSTEM_DESIGN">System Design</option>
                  <option value="BEHAVIORAL">Behavioral / Leadership</option>
                  <option value="HIRING_MANAGER">Hiring Manager Chat</option>
                  <option value="CODING_OA">Live Coding / OA</option>
                  <option value="PANEL">Virtual Onsite Panel</option>
                  <option value="FINAL">Final Executive Round</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Job Description / Notes (Optional)</label>
                <textarea
                  rows={3}
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Paste snippet or tech stack details..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsBriefModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isGeneratingBrief}
                  className="bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs px-5 py-2.5 rounded-xl shadow-md transition-all flex items-center gap-2"
                >
                  {isGeneratingBrief ? 'Generating...' : 'Generate Brief'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Record Interview */}
      {isScheduleModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 max-w-lg w-full space-y-5 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Calendar className="w-5 h-5 text-sky-400" />
              Record Scheduled Interview
            </h3>
            <form onSubmit={handleScheduleInterview} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Company</label>
                <input
                  type="text"
                  required
                  value={schedCompany}
                  onChange={(e) => setSchedCompany(e.target.value)}
                  placeholder="e.g. Datadog"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Session Title</label>
                <input
                  type="text"
                  required
                  value={schedTitle}
                  onChange={(e) => setSchedTitle(e.target.value)}
                  placeholder="e.g. System Design Architecture Screen"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Round Type</label>
                  <select
                    value={schedRound}
                    onChange={(e) => setSchedRound(e.target.value as any)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-sky-500"
                  >
                    <option value="TECHNICAL_SCREEN">Technical Screen</option>
                    <option value="SYSTEM_DESIGN">System Design</option>
                    <option value="BEHAVIORAL">Behavioral</option>
                    <option value="HIRING_MANAGER">Hiring Manager</option>
                    <option value="CODING_OA">Coding / OA</option>
                    <option value="PANEL">Panel</option>
                    <option value="FINAL">Final</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Date & Time</label>
                  <input
                    type="datetime-local"
                    required
                    value={schedDate}
                    onChange={(e) => setSchedDate(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Meeting Link (Zoom / Meet / Teams)</label>
                <input
                  type="url"
                  value={schedMeetingUrl}
                  onChange={(e) => setSchedMeetingUrl(e.target.value)}
                  placeholder="https://zoom.us/j/..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsScheduleModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs px-5 py-2.5 rounded-xl shadow-md transition-all"
                >
                  Save Interview
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
