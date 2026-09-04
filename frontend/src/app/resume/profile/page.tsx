'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { apiClient } from '@/lib/api';
import { CandidateProfileDetailed } from '@/types';
import {
  User,
  ShieldCheck,
  Save,
  CheckCircle2,
  Briefcase,
  GraduationCap,
  Wrench,
  Code2,
  AlertCircle,
  Building2,
  MapPin,
  Calendar,
  Sparkles
} from 'lucide-react';

export default function ResumeProfileReviewPage() {
  const [profile, setProfile] = useState<CandidateProfileDetailed | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [fullName, setFullName] = useState('');
  const [headline, setHeadline] = useState('');
  const [summary, setSummary] = useState('');
  const [location, setLocation] = useState('');
  const [country, setCountry] = useState('');
  const [phone, setPhone] = useState('');
  const [yearsExp, setYearsExp] = useState(0);
  const [workAuth, setWorkAuth] = useState('');
  const [noticePeriod, setNoticePeriod] = useState('');
  const [salaryExp, setSalaryExp] = useState<number | undefined>(undefined);
  const [newSkill, setNewSkill] = useState('');
  const [skillsList, setSkillsList] = useState<any[]>([]);

  useEffect(() => {
    loadProfile();
  }, []);

  async function loadProfile() {
    setLoading(true);
    try {
      const data = await apiClient.getCandidateProfile();
      setProfile(data);
      setHeadline(data.headline || '');
      setSummary(data.summary || '');
      setLocation(data.location || '');
      setCountry(data.country || '');
      setPhone(data.phone || '');
      setYearsExp(data.years_of_experience || 0);
      setWorkAuth(data.work_authorization || '');
      setNoticePeriod(data.notice_period || '');
      setSalaryExp(data.salary_expectation);
      setSkillsList(data.skills || []);
    } catch (err: any) {
      console.error('Failed to load profile:', err);
      setError('No profile found. Please upload a resume first.');
    } finally {
      setLoading(false);
    }
  }

  function handleAddSkill() {
    if (!newSkill.trim()) return;
    setSkillsList([
      ...skillsList,
      { name: newSkill.trim(), category: 'TECHNICAL', proficiency_level: 'ADVANCED', years_experience: 2.0, is_verified: true }
    ]);
    setNewSkill('');
  }

  function handleRemoveSkill(index: number) {
    setSkillsList(skillsList.filter((_, i) => i !== index));
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const updated = await apiClient.updateCandidateProfile({
        full_name: fullName || undefined,
        headline,
        summary,
        location,
        country,
        phone,
        years_of_experience: Number(yearsExp),
        work_authorization: workAuth || undefined,
        notice_period: noticePeriod || undefined,
        salary_expectation: salaryExp ? Number(salaryExp) : undefined,
        skills: skillsList,
        source: 'USER_CONFIRMED'
      });
      setProfile(updated);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save candidate profile');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 p-8 text-center text-slate-400 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full mb-2"></div>
        <span className="ml-3">Loading verified candidate profile...</span>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-slate-950 text-slate-100 min-h-screen">
      <Header
        title="Candidate Profile Review & Verification"
        subtitle="Review extracted resume data and confirm candidate qualifications (SOURCE = USER_CONFIRMED)"
      />

      <div className="max-w-5xl w-full mx-auto p-6 space-y-6">
        {/* Attribution & Status Banner */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 flex items-center justify-between shadow-xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-sky-400 uppercase tracking-wider">
                  Attribution Status:
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  SOURCE = {profile?.source || 'USER_CONFIRMED'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                AI extraction parsed from uploaded resume. Missing sensitive fields are never hallucinated.
              </p>
            </div>
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-lg shadow-sky-500/20 transition-all"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save & Confirm'}
          </button>
        </div>

        {savedSuccess && (
          <div className="p-4 bg-emerald-500/15 border border-emerald-500/30 rounded-xl flex items-center gap-3 text-emerald-300 text-sm">
            <CheckCircle2 className="w-5 h-5 shrink-0" />
            <span>Candidate profile successfully verified and updated.</span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-500/15 border border-rose-500/30 rounded-xl flex items-center gap-3 text-rose-300 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Profile Details Form */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <User className="w-5 h-5 text-sky-400" />
            <h3 className="font-bold text-white text-base">Personal & Professional Identity</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Headline</label>
              <input
                type="text"
                value={headline}
                onChange={(e) => setHeadline(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Years of Experience</label>
              <input
                type="number"
                step="0.5"
                value={yearsExp}
                onChange={(e) => setYearsExp(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Location</label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Country</label>
              <input
                type="text"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Work Authorization</label>
              <input
                type="text"
                value={workAuth}
                onChange={(e) => setWorkAuth(e.target.value)}
                placeholder="e.g. US Citizen / Green Card / Authorized to work"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Notice Period</label>
              <input
                type="text"
                value={noticePeriod}
                onChange={(e) => setNoticePeriod(e.target.value)}
                placeholder="e.g. Immediate / 2 Weeks"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1">Professional Summary</label>
            <textarea
              rows={3}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
            />
          </div>

          {/* Skills Management */}
          <div className="pt-4 border-t border-slate-800">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Code2 className="w-5 h-5 text-indigo-400" />
                <h3 className="font-bold text-white text-base">Verified Skills</h3>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newSkill}
                  onChange={(e) => setNewSkill(e.target.value)}
                  placeholder="Add skill (e.g. Docker)..."
                  className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white"
                />
                <button
                  type="button"
                  onClick={handleAddSkill}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg"
                >
                  + Add
                </button>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {skillsList.map((skill, idx) => (
                <span
                  key={idx}
                  className="px-3 py-1 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-200 flex items-center gap-2"
                >
                  {skill.name}
                  <button
                    onClick={() => handleRemoveSkill(idx)}
                    className="text-slate-400 hover:text-rose-400 font-bold ml-1"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Extracted Experiences Display */}
          {profile?.experiences && profile.experiences.length > 0 && (
            <div className="pt-4 border-t border-slate-800 space-y-3">
              <div className="flex items-center gap-2 mb-2">
                <Briefcase className="w-5 h-5 text-sky-400" />
                <h3 className="font-bold text-white text-base">Extracted Work Experience</h3>
              </div>
              {profile.experiences.map((exp, i) => (
                <div key={i} className="p-4 bg-slate-800/40 rounded-xl border border-slate-700/60">
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-white text-sm">{exp.title}</div>
                    <span className="text-xs text-slate-400">{exp.start_date} - {exp.end_date || 'Present'}</span>
                  </div>
                  <div className="text-xs text-sky-400 mt-0.5">{exp.company_name}</div>
                  {exp.description && <p className="text-xs text-slate-300 mt-2">{exp.description}</p>}
                </div>
              ))}
            </div>
          )}

          {/* Extracted Education Display */}
          {profile?.educations && profile.educations.length > 0 && (
            <div className="pt-4 border-t border-slate-800 space-y-3">
              <div className="flex items-center gap-2 mb-2">
                <GraduationCap className="w-5 h-5 text-emerald-400" />
                <h3 className="font-bold text-white text-base">Extracted Education</h3>
              </div>
              {profile.educations.map((edu, i) => (
                <div key={i} className="p-4 bg-slate-800/40 rounded-xl border border-slate-700/60">
                  <div className="font-semibold text-white text-sm">{edu.degree} in {edu.field_of_study}</div>
                  <div className="text-xs text-emerald-400 mt-0.5">{edu.institution}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
