'use client';

import React, { useEffect, useState } from 'react';
import { Header } from '@/components/Header';
import {
  Zap,
  ShieldCheck,
  Play,
  Sliders,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Briefcase,
  DollarSign,
  RefreshCw,
  Plus,
  Trash2,
  Activity,
  Layers,
} from 'lucide-react';
import { api } from '@/lib/api';
import { ApplicationPolicy, AutoApplyStatus, ApplicationQueueItem } from '@/types';

export default function AutoApplyDashboard() {
  const [policy, setPolicy] = useState<ApplicationPolicy | null>(null);
  const [status, setStatus] = useState<AutoApplyStatus | null>(null);
  const [queue, setQueue] = useState<ApplicationQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [processingQueue, setProcessingQueue] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Form states for tag inputs
  const [newBlockedCompany, setNewBlockedCompany] = useState('');
  const [newBlockedKeyword, setNewBlockedKeyword] = useState('');
  const [newPreferredRole, setNewPreferredRole] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      const [policyRes, statusRes, queueRes] = await Promise.all([
        api.getAutoApplyPolicy(),
        api.getAutoApplyStatus(),
        api.getAutoApplyQueue(),
      ]);
      setPolicy(policyRes);
      setStatus(statusRes);
      setQueue(queueRes);
    } catch (err: any) {
      console.error('Failed to load auto-apply data:', err);
      setMessage({ type: 'error', text: err.message || 'Failed to load policy.' });
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleAutoApply() {
    if (!policy) return;
    const newEnabled = !policy.auto_apply_enabled;
    setPolicy({ ...policy, auto_apply_enabled: newEnabled });
    try {
      await api.updateAutoApplyPolicy({ auto_apply_enabled: newEnabled });
      const updatedStatus = await api.getAutoApplyStatus();
      setStatus(updatedStatus);
      setMessage({
        type: 'success',
        text: `Automated application engine has been ${newEnabled ? 'ENABLED' : 'PAUSED'}.`,
      });
    } catch (err: any) {
      setMessage({ type: 'error', text: `Failed to update status: ${err.message}` });
    }
  }

  async function handleSavePolicy(e: React.FormEvent) {
    e.preventDefault();
    if (!policy) return;
    setSaving(true);
    setMessage(null);
    try {
      const updated = await api.updateAutoApplyPolicy({
        minimum_match_score: policy.minimum_match_score,
        minimum_salary: policy.minimum_salary ? Number(policy.minimum_salary) : null,
        maximum_experience: policy.maximum_experience ? Number(policy.maximum_experience) : null,
        preferred_roles: policy.preferred_roles,
        blocked_roles: policy.blocked_roles,
        blocked_companies: policy.blocked_companies,
        blocked_keywords: policy.blocked_keywords,
        allowed_employment_types: policy.allowed_employment_types,
        daily_application_limit: policy.daily_application_limit,
        per_source_daily_limit: policy.per_source_daily_limit,
        duplicate_protection: policy.duplicate_protection,
        allow_remote: policy.allow_remote,
        allow_hybrid: policy.allow_hybrid,
        allow_onsite: policy.allow_onsite,
      });
      setPolicy(updated);
      const updatedStatus = await api.getAutoApplyStatus();
      setStatus(updatedStatus);
      setMessage({ type: 'success', text: 'Auto-apply policy rules saved successfully.' });
    } catch (err: any) {
      setMessage({ type: 'error', text: `Failed to save policy: ${err.message}` });
    } finally {
      setSaving(false);
    }
  }

  async function handleProcessQueue() {
    try {
      setProcessingQueue(true);
      setMessage(null);
      const res = await api.processApplicationQueue(5);
      const [updatedStatus, updatedQueue] = await Promise.all([
        api.getAutoApplyStatus(),
        api.getAutoApplyQueue(),
      ]);
      setStatus(updatedStatus);
      setQueue(updatedQueue);
      setMessage({
        type: 'success',
        text: `Queue processing complete: processed ${res.processed_count} applications.`,
      });
    } catch (err: any) {
      setMessage({ type: 'error', text: `Queue processing failed: ${err.message}` });
    } finally {
      setProcessingQueue(false);
    }
  }

  // Tag helper functions
  const addTag = (field: 'blocked_companies' | 'blocked_keywords' | 'preferred_roles' | 'blocked_roles', value: string, setter: (val: string) => void) => {
    if (!policy || !value.trim()) return;
    if (!policy[field].includes(value.trim())) {
      setPolicy({ ...policy, [field]: [...policy[field], value.trim()] });
    }
    setter('');
  };

  const removeTag = (field: 'blocked_companies' | 'blocked_keywords' | 'preferred_roles' | 'blocked_roles', tag: string) => {
    if (!policy) return;
    setPolicy({ ...policy, [field]: policy[field].filter((t) => t !== tag) });
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col h-screen">
        <Header title="Auto-Apply Engine" subtitle="Configuring autonomous application policies & queue" />
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-3 text-slate-500 font-medium">
            <RefreshCw className="w-5 h-5 animate-spin text-sky-600" />
            Loading policy and queue status...
          </div>
        </div>
      </div>
    );
  }

  const isDailyLimited = typeof status?.daily_application_limit === 'number' && status.daily_application_limit > 0;
  const quotaPercent = isDailyLimited && status?.daily_application_limit
    ? Math.min(100, Math.round(((status.today_applications_count ?? status.applications_submitted_today ?? 0) / status.daily_application_limit) * 100))
    : 0;

  return (
    <div className="flex-1 flex flex-col h-screen overflow-y-auto bg-slate-50">
      <Header
        title="Automated Application Engine"
        subtitle="Autonomous policy engine, verified data mapping, and submission queue"
      />

      <div className="p-6 max-w-7xl mx-auto w-full space-y-6">
        {/* Compliance Guarantee Banner */}
        <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-2xl p-4 flex items-start gap-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-emerald-900">Safety & Compliance Non-Circumvention Policy</h3>
              <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">ACTIVE</span>
            </div>
            <p className="text-xs text-emerald-700/90 mt-1 leading-relaxed">
              Auto-Apply strictly uses authorized partner APIs. No web-scraping, anti-bot circumvention, or CAPTCHA bypass is performed. Only verified profile data is mapped; missing required form answers are paused for manual review.
            </p>
          </div>
        </div>

        {/* Message Feedback */}
        {message && (
          <div
            className={`p-4 rounded-xl border flex items-center gap-3 text-sm font-medium ${
              message.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : 'bg-rose-50 text-rose-800 border-rose-200'
            }`}
          >
            {message.type === 'success' ? <CheckCircle2 className="w-5 h-5 text-emerald-600" /> : <AlertTriangle className="w-5 h-5 text-rose-600" />}
            <span>{message.text}</span>
          </div>
        )}

        {/* Status Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Main Toggle Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Engine Status</span>
              <span
                className={`w-3 h-3 rounded-full ${
                  policy?.auto_apply_enabled ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300'
                }`}
              />
            </div>
            <div className="my-3">
              <span
                className={`text-2xl font-black ${
                  policy?.auto_apply_enabled ? 'text-emerald-600' : 'text-slate-400'
                }`}
              >
                {policy?.auto_apply_enabled ? 'ACTIVE' : 'PAUSED'}
              </span>
            </div>
            <button
              onClick={handleToggleAutoApply}
              className={`w-full py-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all ${
                policy?.auto_apply_enabled
                  ? 'bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200'
                  : 'bg-sky-600 text-white hover:bg-sky-700 shadow-sm'
              }`}
            >
              {policy?.auto_apply_enabled ? (
                <>
                  <XCircle className="w-4 h-4" /> Pause Auto-Apply
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" /> Enable Auto-Apply
                </>
              )}
            </button>
          </div>

          {/* Daily Quota Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                {isDailyLimited ? "Today's Quota" : "Today's Applications"}
              </span>
              <Activity className="w-4 h-4 text-sky-500" />
            </div>
            <div className="my-3">
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-black text-slate-900">{status?.today_applications_count ?? status?.applications_submitted_today ?? 0}</span>
                <span className="text-sm font-medium text-slate-400">
                  {isDailyLimited ? `/ ${status?.daily_application_limit} max` : '/ Unlimited'}
                </span>
              </div>
              {isDailyLimited ? (
                <div className="w-full bg-slate-100 rounded-full h-2 mt-2 overflow-hidden">
                  <div
                    className={`h-full transition-all ${quotaPercent >= 90 ? 'bg-rose-500' : 'bg-sky-500'}`}
                    style={{ width: `${quotaPercent}%` }}
                  />
                </div>
              ) : (
                <div className="mt-2 text-xs font-medium text-emerald-600 flex items-center gap-1.5">
                  <span className="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
                  True Unlimited Mode Active
                </div>
              )}
            </div>
            <span className="text-xs text-slate-500 font-medium">
              {isDailyLimited
                ? `${status?.remaining_daily_quota ?? 0} submissions remaining today`
                : "Unlimited applications subject to platform/provider limits."}
            </span>
          </div>

          {/* Queue Count Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Queue Pending</span>
              <Clock className="w-4 h-4 text-amber-500" />
            </div>
            <div className="my-3">
              <span className="text-2xl font-black text-slate-900">{queue.length}</span>
              <span className="text-xs text-slate-400 block mt-1">jobs awaiting worker execution</span>
            </div>
            <button
              onClick={handleProcessQueue}
              disabled={processingQueue || queue.length === 0}
              className="w-full py-2.5 rounded-xl font-bold text-xs bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Play className={`w-3.5 h-3.5 ${processingQueue ? 'animate-spin' : ''}`} />
              {processingQueue ? 'Processing...' : 'Process Queue Now'}
            </button>
          </div>

          {/* Lifetime Success Rate */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Lifetime Auto-Applied</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>
            <div className="my-3">
              <span className="text-2xl font-black text-emerald-600">{status?.total_applied || 0}</span>
              <span className="text-xs text-slate-400 block mt-1">{status?.total_failed || 0} failed / rejected</span>
            </div>
            <span className="text-xs font-bold text-slate-600">
              Threshold: {policy?.minimum_match_score || 85}% min score
            </span>
          </div>
        </div>

        {/* Two Column Layout: Policy Settings & Live Queue */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Policy Settings Form (7 cols) */}
          <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Sliders className="w-5 h-5 text-sky-600" />
                <h2 className="text-base font-bold text-slate-900">Auto-Apply Policy Rules</h2>
              </div>
              <span className="text-xs text-slate-500">Fine-grained candidate decision rules</span>
            </div>

            {policy && (
              <form onSubmit={handleSavePolicy} className="mt-6 space-y-6">
                {/* Match Score Threshold Slider */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Minimum Match Score Required
                    </label>
                    <span className="text-sm font-black text-sky-600 bg-sky-50 px-2.5 py-0.5 rounded-lg border border-sky-200">
                      {policy.minimum_match_score}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="98"
                    step="1"
                    value={policy.minimum_match_score}
                    onChange={(e) => setPolicy({ ...policy, minimum_match_score: Number(e.target.value) })}
                    className="w-full accent-sky-600 cursor-pointer"
                  />
                  <p className="text-[11px] text-slate-500">
                    Jobs scoring below this threshold will automatically be skipped by the policy engine.
                  </p>
                </div>

                {/* Salary & Experience Boundaries */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold text-slate-700 block mb-1">Minimum Base Salary ($ USD)</label>
                    <div className="relative">
                      <DollarSign className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                      <input
                        type="number"
                        placeholder="e.g. 120000"
                        value={policy.minimum_salary || ''}
                        onChange={(e) => setPolicy({ ...policy, minimum_salary: e.target.value ? Number(e.target.value) : undefined })}
                        className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-700 block mb-1">Max Experience Required (Years)</label>
                    <div className="relative">
                      <Briefcase className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                      <input
                        type="number"
                        placeholder="e.g. 6"
                        value={policy.maximum_experience || ''}
                        onChange={(e) => setPolicy({ ...policy, maximum_experience: e.target.value ? Number(e.target.value) : undefined })}
                        className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500"
                      />
                    </div>
                  </div>
                </div>

                {/* Work Arrangement Checkboxes */}
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-2">Allowed Work Arrangements</label>
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { key: 'allow_remote', label: 'Remote' },
                      { key: 'allow_hybrid', label: 'Hybrid' },
                      { key: 'allow_onsite', label: 'Onsite' },
                    ].map(({ key, label }) => (
                      <label
                        key={key}
                        className={`flex items-center gap-2 p-3 rounded-xl border cursor-pointer transition-all ${
                          (policy as any)[key]
                            ? 'bg-sky-50 border-sky-300 text-sky-900 font-bold'
                            : 'bg-slate-50 border-slate-200 text-slate-600'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={(policy as any)[key]}
                          onChange={(e) => setPolicy({ ...policy, [key]: e.target.checked })}
                          className="accent-sky-600"
                        />
                        <span className="text-xs">{label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Preferred Roles Tag Input */}
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Preferred Job Roles (Whitelist)</label>
                  <div className="flex gap-2 mb-2">
                    <input
                      type="text"
                      placeholder="e.g. Backend Engineer"
                      value={newPreferredRole}
                      onChange={(e) => setNewPreferredRole(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('preferred_roles', newPreferredRole, setNewPreferredRole))}
                      className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-slate-200"
                    />
                    <button
                      type="button"
                      onClick={() => addTag('preferred_roles', newPreferredRole, setNewPreferredRole)}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-lg"
                    >
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5 min-h-[28px]">
                    {policy.preferred_roles.map((tag) => (
                      <span key={tag} className="inline-flex items-center gap-1 text-xs bg-sky-100 text-sky-800 px-2.5 py-1 rounded-full">
                        {tag}
                        <button type="button" onClick={() => removeTag('preferred_roles', tag)}><Trash2 className="w-3 h-3 hover:text-rose-600" /></button>
                      </span>
                    ))}
                    {policy.preferred_roles.length === 0 && (
                      <span className="text-[11px] text-slate-400 italic">No specific role filter (all matched titles eligible)</span>
                    )}
                  </div>
                </div>

                {/* Blocked Companies Tag Input */}
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Blocked Companies (Blacklist)</label>
                  <div className="flex gap-2 mb-2">
                    <input
                      type="text"
                      placeholder="e.g. Acme Corp"
                      value={newBlockedCompany}
                      onChange={(e) => setNewBlockedCompany(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('blocked_companies', newBlockedCompany, setNewBlockedCompany))}
                      className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-slate-200"
                    />
                    <button
                      type="button"
                      onClick={() => addTag('blocked_companies', newBlockedCompany, setNewBlockedCompany)}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-lg"
                    >
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5 min-h-[28px]">
                    {policy.blocked_companies.map((tag) => (
                      <span key={tag} className="inline-flex items-center gap-1 text-xs bg-rose-100 text-rose-800 px-2.5 py-1 rounded-full">
                        {tag}
                        <button type="button" onClick={() => removeTag('blocked_companies', tag)}><Trash2 className="w-3 h-3 hover:text-rose-600" /></button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Blocked Keywords Tag Input */}
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Blocked Keywords (Blacklist)</label>
                  <div className="flex gap-2 mb-2">
                    <input
                      type="text"
                      placeholder="e.g. unpaid, commission-only, crypto"
                      value={newBlockedKeyword}
                      onChange={(e) => setNewBlockedKeyword(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('blocked_keywords', newBlockedKeyword, setNewBlockedKeyword))}
                      className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-slate-200"
                    />
                    <button
                      type="button"
                      onClick={() => addTag('blocked_keywords', newBlockedKeyword, setNewBlockedKeyword)}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-lg"
                    >
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5 min-h-[28px]">
                    {policy.blocked_keywords.map((tag) => (
                      <span key={tag} className="inline-flex items-center gap-1 text-xs bg-amber-100 text-amber-800 px-2.5 py-1 rounded-full">
                        {tag}
                        <button type="button" onClick={() => removeTag('blocked_keywords', tag)}><Trash2 className="w-3 h-3 hover:text-rose-600" /></button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Daily Limits */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-xs font-bold text-slate-700">Global Daily Limit</label>
                      <button
                        type="button"
                        onClick={() => setPolicy({ ...policy, daily_application_limit: policy.daily_application_limit ? null : 30 })}
                        className="text-[10px] font-semibold text-sky-600 hover:text-sky-700"
                      >
                        {policy.daily_application_limit ? 'Set Unlimited' : 'Set Cap'}
                      </button>
                    </div>
                    <input
                      type="number"
                      min="1"
                      placeholder="Unlimited (no daily cap)"
                      value={policy.daily_application_limit ?? ''}
                      onChange={(e) => {
                        const val = e.target.value.trim();
                        setPolicy({ ...policy, daily_application_limit: val === '' ? null : Number(val) });
                      }}
                      className="w-full px-3 py-2 text-sm rounded-xl border border-slate-200"
                    />
                    <span className="text-[10px] text-slate-400 mt-1 block">Leave blank for Unlimited</span>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-xs font-bold text-slate-700">Per-Source Limit</label>
                      <button
                        type="button"
                        onClick={() => setPolicy({ ...policy, per_source_daily_limit: policy.per_source_daily_limit ? null : 10 })}
                        className="text-[10px] font-semibold text-sky-600 hover:text-sky-700"
                      >
                        {policy.per_source_daily_limit ? 'Set Unlimited' : 'Set Cap'}
                      </button>
                    </div>
                    <input
                      type="number"
                      min="1"
                      placeholder="Unlimited"
                      value={policy.per_source_daily_limit ?? ''}
                      onChange={(e) => {
                        const val = e.target.value.trim();
                        setPolicy({ ...policy, per_source_daily_limit: val === '' ? null : Number(val) });
                      }}
                      className="w-full px-3 py-2 text-sm rounded-xl border border-slate-200"
                    />
                    <span className="text-[10px] text-slate-400 mt-1 block">Leave blank for Unlimited</span>
                  </div>
                </div>

                {/* Submit button */}
                <button
                  type="submit"
                  disabled={saving}
                  className="w-full py-3 rounded-xl bg-sky-600 text-white font-bold text-sm hover:bg-sky-700 transition-colors shadow-sm disabled:opacity-50"
                >
                  {saving ? 'Saving Policy Settings...' : 'Save Policy Changes'}
                </button>
              </form>
            )}
          </div>

          {/* Live Queue Items Viewer (5 cols) */}
          <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-indigo-600" />
                <h2 className="text-base font-bold text-slate-900">Application Queue</h2>
              </div>
              <button
                onClick={loadData}
                className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Refresh
              </button>
            </div>

            <div className="mt-4 flex-1 overflow-y-auto space-y-3 max-h-[600px]">
              {queue.length === 0 ? (
                <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  <Clock className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <h4 className="text-sm font-bold text-slate-700">Queue is Empty</h4>
                  <p className="text-xs text-slate-500 mt-1">
                    Matched jobs that meet your auto-apply policy will automatically appear here.
                  </p>
                </div>
              ) : (
                queue.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:border-indigo-300 transition-all space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="text-xs font-bold text-slate-900 line-clamp-1">
                          {item.job?.title || 'Job Application'}
                        </h4>
                        <span className="text-[11px] text-slate-500 font-medium">
                          {item.job?.company_name || 'Partner Platform'}
                        </span>
                      </div>
                      <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-md bg-amber-100 text-amber-800 border border-amber-200">
                        {item.status}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                      <span>Priority: {item.priority}</span>
                      <span>Attempt: {item.attempt_count} / {item.max_attempts}</span>
                      <span>{new Date(item.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>

                    {item.error_message && (
                      <div className="text-[10px] text-rose-700 bg-rose-50 p-2 rounded-lg border border-rose-100 leading-tight">
                        {item.error_message}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
