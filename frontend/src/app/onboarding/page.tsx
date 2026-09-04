'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Header } from '@/components/Header';
import { apiClient } from '@/lib/api';
import { OnboardingState } from '@/types';
import {
  CheckCircle2,
  ChevronRight,
  ChevronLeft,
  Upload,
  User,
  Briefcase,
  Sliders,
  Mail,
  Cpu,
  Layers,
  FileCheck,
  Sparkles,
  AlertCircle
} from 'lucide-react';

const STEPS = [
  { id: 1, title: 'Welcome', desc: 'Introduction to AI Job Assistant', icon: Sparkles },
  { id: 2, title: 'Profile Setup', desc: 'Candidate verification', icon: User },
  { id: 3, title: 'Resume Upload', desc: 'Structured resume parsing', icon: Upload },
  { id: 4, title: 'Job Preferences', desc: 'Roles, salaries, and remote targets', icon: Briefcase },
  { id: 5, title: 'Auto-Apply Policy', desc: 'Compliance & rate control rules', icon: Sliders },
  { id: 6, title: 'Mailbox Connect', desc: 'OAuth Gmail / Outlook integration', icon: Mail },
  { id: 7, title: 'AI OmniRoute', desc: 'Model gateway configuration', icon: Cpu },
  { id: 8, title: 'Integrations', desc: 'Job platform connectors', icon: Layers },
  { id: 9, title: 'Review & Verify', desc: 'Candidate confirmation', icon: FileCheck },
  { id: 10, title: 'Complete', desc: 'Ready for production job discovery', icon: CheckCircle2 },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [state, setState] = useState<OnboardingState | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [fullName, setFullName] = useState('');
  const [headline, setHeadline] = useState('');
  const [location, setLocation] = useState('');
  const [country, setCountry] = useState('');
  const [phone, setPhone] = useState('');
  const [roles, setRoles] = useState('Senior Backend Engineer, Full Stack Lead');
  const [minSalary, setMinSalary] = useState(140000);
  const [autoApplyEnabled, setAutoApplyEnabled] = useState(false);
  const [minScore, setMinScore] = useState(85);

  useEffect(() => {
    loadState();
  }, []);

  async function loadState() {
    setLoading(true);
    try {
      const res = await apiClient.getOnboardingState();
      setState(res);
      setCurrentStep(res.current_step || 1);
      setFullName(res.full_name || '');
    } catch (err: any) {
      console.error('Failed to load onboarding state:', err);
    } finally {
      setLoading(false);
    }
  }

  async function goToStep(stepNum: number) {
    setSaving(true);
    setError(null);
    try {
      await apiClient.updateOnboardingStep(stepNum);
      setCurrentStep(stepNum);
    } catch (err: any) {
      setError(err.message || 'Failed to update onboarding step');
    } finally {
      setSaving(false);
    }
  }

  async function finishOnboarding() {
    setSaving(true);
    setError(null);
    try {
      await apiClient.completeOnboarding();
      router.push('/recommended');
    } catch (err: any) {
      setError(err.message || 'Failed to complete onboarding');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 p-8 text-center text-slate-400 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full mb-2"></div>
        <span className="ml-3">Loading onboarding journey...</span>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-slate-950 text-slate-100 min-h-screen">
      <Header
        title="Candidate Production Onboarding"
        subtitle="10-step verified configuration journey for AI Job Assistant"
      />

      <div className="max-w-6xl w-full mx-auto p-6 space-y-6">
        {/* Progress Bar & Steps Tracker */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <span className="text-xs font-semibold text-sky-400 uppercase tracking-wider">
                Step {currentStep} of {STEPS.length}
              </span>
              <h2 className="text-lg font-bold text-white mt-0.5">
                {STEPS[currentStep - 1].title}: {STEPS[currentStep - 1].desc}
              </h2>
            </div>
            <div className="text-xs font-medium text-slate-400 bg-slate-800 px-3 py-1.5 rounded-lg">
              {Math.round((currentStep / STEPS.length) * 100)}% Completed
            </div>
          </div>

          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden mb-6">
            <div
              className="bg-gradient-to-r from-sky-500 to-indigo-500 h-full transition-all duration-300 rounded-full"
              style={{ width: `${(currentStep / STEPS.length) * 100}%` }}
            />
          </div>

          {/* Stepper Dots */}
          <div className="grid grid-cols-5 md:grid-cols-10 gap-2">
            {STEPS.map((s) => {
              const Icon = s.icon;
              const isPast = s.id < currentStep;
              const isCurrent = s.id === currentStep;
              return (
                <button
                  key={s.id}
                  onClick={() => goToStep(s.id)}
                  className={`flex flex-col items-center p-2 rounded-xl text-center transition-all ${
                    isCurrent
                      ? 'bg-sky-500/20 border border-sky-500/50 text-sky-300'
                      : isPast
                      ? 'bg-slate-800/60 border border-slate-700/50 text-emerald-400 hover:bg-slate-800'
                      : 'bg-slate-900 border border-slate-800/60 text-slate-500 hover:bg-slate-800/40'
                  }`}
                >
                  <Icon className="w-4 h-4 mb-1" />
                  <span className="text-[11px] font-semibold truncate w-full">{s.title}</span>
                </button>
              );
            })}
          </div>
        </div>

        {error && (
          <div className="p-4 bg-rose-500/15 border border-rose-500/30 rounded-xl flex items-center gap-3 text-rose-300 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Step Content Container */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-8 shadow-xl min-h-[400px] flex flex-col justify-between">
          {/* STEP 1: WELCOME */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-sky-500/10 border border-sky-500/30 rounded-full text-xs font-semibold text-sky-400">
                <Sparkles className="w-3.5 h-3.5" /> Welcome Candidate
              </div>
              <h3 className="text-2xl font-bold text-white">Welcome to AI Job Assistant</h3>
              <p className="text-slate-300 text-sm leading-relaxed max-w-3xl">
                This production onboarding setup connects your resume intelligence, job discovery sources,
                authorized auto-apply policies, AI model routing, and recruiter mailboxes into a single safe workspace.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
                <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/60">
                  <div className="font-semibold text-white text-sm">Zero Hallucinations</div>
                  <p className="text-xs text-slate-400 mt-1">Verified candidate profile data with exact attribution tracking.</p>
                </div>
                <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/60">
                  <div className="font-semibold text-white text-sm">Strict Compliance</div>
                  <p className="text-xs text-slate-400 mt-1">Non-circumvention enforcement. Zero fake bot submissions.</p>
                </div>
                <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/60">
                  <div className="font-semibold text-white text-sm">OmniRoute AI</div>
                  <p className="text-xs text-slate-400 mt-1">Flexible model switching and resilient fallback capabilities.</p>
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: PROFILE SETUP */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <h3 className="text-xl font-bold text-white">Candidate Information</h3>
              <p className="text-xs text-slate-400">Verified personal details. Sensitive items remain blank unless explicitly entered.</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1">Full Name</label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="Jane Doe"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1">Professional Headline</label>
                  <input
                    type="text"
                    value={headline}
                    onChange={(e) => setHeadline(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="Senior Backend Architect"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1">City / Region</label>
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="San Francisco, CA"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1">Country</label>
                  <input
                    type="text"
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="United States"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1">Phone (Optional)</label>
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="+1 (555) 019-2834"
                  />
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: RESUME UPLOAD */}
          {currentStep === 3 && (
            <div className="space-y-4">
              <h3 className="text-xl font-bold text-white">Resume Ingestion</h3>
              <p className="text-xs text-slate-400">Upload your PDF or DOCX resume for automated section parsing.</p>
              <div className="border-2 border-dashed border-slate-700 hover:border-sky-500 rounded-2xl p-8 text-center transition-all bg-slate-800/30">
                <Upload className="w-10 h-10 text-sky-400 mx-auto mb-3" />
                <h4 className="font-semibold text-white text-sm mb-1">Drag & Drop Resume File</h4>
                <p className="text-xs text-slate-400 mb-4">Supported formats: PDF, DOCX (Max 10MB)</p>
                <button
                  onClick={() => router.push('/resume')}
                  className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-sky-500/20"
                >
                  Go to Resume Center
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: JOB PREFERENCES */}
          {currentStep === 4 && (
            <div className="space-y-4">
              <h3 className="text-xl font-bold text-white">Target Job Preferences</h3>
              <p className="text-xs text-slate-400">Set target roles, location constraints, and salary expectations.</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1">Target Job Titles (Comma-separated)</label>
                  <input
                    type="text"
                    value={roles}
                    onChange={(e) => setRoles(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1">Minimum Base Salary (USD)</label>
                  <input
                    type="number"
                    value={minSalary}
                    onChange={(e) => setMinSalary(Number(e.target.value))}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>
              </div>
            </div>
          )}

          {/* STEP 5: AUTO-APPLY POLICY */}
          {currentStep === 5 && (
            <div className="space-y-4">
              <h3 className="text-xl font-bold text-white">Automated Application Policy</h3>
              <p className="text-xs text-slate-400">Control thresholds for authorized partner platform submissions.</p>
              <div className="space-y-3">
                <label className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-xl border border-slate-700/60 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoApplyEnabled}
                    onChange={(e) => setAutoApplyEnabled(e.target.checked)}
                    className="w-4 h-4 rounded text-sky-500"
                  />
                  <div>
                    <span className="text-sm font-semibold text-white block">Enable Auto-Apply for Authorized Connectors</span>
                    <span className="text-xs text-slate-400">Allows direct API submissions for verified matching requisitions.</span>
                  </div>
                </label>
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1">Minimum AI Match Score (%): {minScore}%</label>
                  <input
                    type="range"
                    min="50"
                    max="95"
                    value={minScore}
                    onChange={(e) => setMinScore(Number(e.target.value))}
                    className="w-full accent-sky-500"
                  />
                </div>
              </div>
            </div>
          )}

          {/* STEP 6: MAILBOX */}
          {currentStep === 6 && (
            <div className="space-y-4">
              <h3 className="text-xl font-bold text-white">Mailbox & Recruiter Sync</h3>
              <p className="text-xs text-slate-400">Connect your inbox via OAuth 2.0 to detect interview invites and recruiter replies.</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="p-4 bg-slate-800/60 border border-slate-700 rounded-xl flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-white text-sm">Google Gmail</div>
                    <div className="text-xs text-slate-400">Official OAuth 2.0</div>
                  </div>
                  <button
                    onClick={() => router.push('/mailbox')}
                    className="px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-lg"
                  >
                    Connect Gmail
                  </button>
                </div>
                <div className="p-4 bg-slate-800/60 border border-slate-700 rounded-xl flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-white text-sm">Microsoft Outlook</div>
                    <div className="text-xs text-slate-400">Graph API OAuth 2.0</div>
                  </div>
                  <button
                    onClick={() => router.push('/mailbox')}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg"
                  >
                    Connect Outlook
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* STEP 7: AI OMNIROUTE */}
          {currentStep === 7 && (
            <div className="space-y-4">
              <h3 className="text-xl font-bold text-white">OmniRoute AI Gateway</h3>
              <p className="text-xs text-slate-400">Configure LLM routing for resume extraction, semantic matching, and drafting.</p>
              <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-white">Active AI Gateway</div>
                  <div className="text-xs text-slate-400">OmniRoute / OpenAI / Gemini / Fallback Mock</div>
                </div>
                <button
                  onClick={() => router.push('/settings/ai')}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs font-semibold rounded-lg"
                >
                  Configure AI Gateway
                </button>
              </div>
            </div>
          )}

          {/* STEP 8: INTEGRATIONS */}
          {currentStep === 8 && (
            <div className="space-y-4">
              <h3 className="text-xl font-bold text-white">Platform Connectors</h3>
              <p className="text-xs text-slate-400">Verify connectors across LinkedIn, Greenhouse, Lever, Naukri, Indeed, and Unstop.</p>
              <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-white">10 Platform Connectors Ready</div>
                  <div className="text-xs text-slate-400">Compliant external application links & verified API channels.</div>
                </div>
                <button
                  onClick={() => router.push('/settings/integrations')}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs font-semibold rounded-lg"
                >
                  View Connectors
                </button>
              </div>
            </div>
          )}

          {/* STEP 9: REVIEW & VERIFY */}
          {currentStep === 9 && (
            <div className="space-y-4">
              <h3 className="text-xl font-bold text-white">Review Verified Profile</h3>
              <p className="text-xs text-slate-400">Confirm all candidate skills and credentials before initiating discovery runs.</p>
              <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-white">Candidate Profile Summary</div>
                  <div className="text-xs text-slate-400">Inspect verified education, skills, and experience items.</div>
                </div>
                <button
                  onClick={() => router.push('/resume/profile')}
                  className="px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-lg"
                >
                  Review Profile
                </button>
              </div>
            </div>
          )}

          {/* STEP 10: COMPLETE */}
          {currentStep === 10 && (
            <div className="space-y-4 text-center py-6">
              <CheckCircle2 className="w-16 h-16 text-emerald-400 mx-auto" />
              <h3 className="text-2xl font-bold text-white">Onboarding Complete!</h3>
              <p className="text-slate-300 text-sm max-w-xl mx-auto leading-relaxed">
                Your candidate profile, job discovery preferences, auto-apply guardrails, and mailbox integrations
                are configured and verified.
              </p>
              <button
                onClick={finishOnboarding}
                disabled={saving}
                className="px-6 py-3 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-bold rounded-xl shadow-lg shadow-sky-500/25 transition-all text-sm mt-4"
              >
                {saving ? 'Finalizing Setup...' : 'Launch Job Assistant Workspace →'}
              </button>
            </div>
          )}

          {/* Stepper Buttons */}
          <div className="flex items-center justify-between border-t border-slate-800 pt-6 mt-8">
            <button
              onClick={() => goToStep(Math.max(1, currentStep - 1))}
              disabled={currentStep === 1 || saving}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all"
            >
              <ChevronLeft className="w-4 h-4" /> Previous
            </button>

            {currentStep < 10 ? (
              <button
                onClick={() => goToStep(currentStep + 1)}
                disabled={saving}
                className="px-5 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-lg shadow-sky-500/20 transition-all"
              >
                {saving ? 'Saving...' : 'Next Step'} <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={finishOnboarding}
                disabled={saving}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-lg shadow-emerald-500/20 transition-all"
              >
                Complete Onboarding <CheckCircle2 className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
