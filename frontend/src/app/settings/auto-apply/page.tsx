'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { apiClient } from '@/lib/api';
import { AutoApplyPolicyConfig } from '@/types';
import {
  Zap,
  ShieldCheck,
  Save,
  CheckCircle2,
  AlertCircle,
  Sliders,
  Layers,
  Lock
} from 'lucide-react';

export default function AutoApplySettingsPage() {
  const [policy, setPolicy] = useState<AutoApplyPolicyConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Policy form states
  const [enabled, setEnabled] = useState(false);
  const [minScore, setMinScore] = useState(85);
  const [dailyLimit, setDailyLimit] = useState(30);
  const [perSourceLimit, setPerSourceLimit] = useState(10);
  const [perCompanyLimit, setPerCompanyLimit] = useState(3);
  const [requireComplete, setRequireComplete] = useState(true);
  const [duplicateProtection, setDuplicateProtection] = useState(true);
  const [allowRemote, setAllowRemote] = useState(true);
  const [allowHybrid, setAllowHybrid] = useState(true);
  const [allowOnsite, setAllowOnsite] = useState(false);

  useEffect(() => {
    loadPolicy();
  }, []);

  async function loadPolicy() {
    setLoading(true);
    try {
      const data = await apiClient.getAutoApplyPolicy();
      setPolicy(data);
      setEnabled(data.auto_apply_enabled);
      setMinScore(data.minimum_match_score || 85);
      setDailyLimit(data.daily_application_limit || 30);
      setPerSourceLimit(data.per_source_daily_limit || 10);
      setPerCompanyLimit(data.per_company_limit || 3);
      setRequireComplete(data.require_complete_profile ?? true);
      setDuplicateProtection(data.duplicate_protection ?? true);
      setAllowRemote(data.allow_remote ?? true);
      setAllowHybrid(data.allow_hybrid ?? true);
      setAllowOnsite(data.allow_onsite ?? false);
    } catch (err: any) {
      console.error('Failed to load auto-apply policy:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const payload: Partial<AutoApplyPolicyConfig> = {
        auto_apply_enabled: enabled,
        minimum_match_score: Number(minScore),
        daily_application_limit: Number(dailyLimit),
        per_source_daily_limit: Number(perSourceLimit),
        per_company_limit: Number(perCompanyLimit),
        require_complete_profile: requireComplete,
        duplicate_protection: duplicateProtection,
        allow_remote: allowRemote,
        allow_hybrid: allowHybrid,
        allow_onsite: allowOnsite
      };

      const updated = await apiClient.updateAutoApplyPolicy(payload);
      setPolicy(updated);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to update auto-apply policy');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 p-8 text-center text-slate-400 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full mb-2"></div>
        <span className="ml-3">Loading auto-apply configuration...</span>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-slate-950 text-slate-100 min-h-screen">
      <Header
        title="Auto-Apply Policy & Compliance Guardrails"
        subtitle="Manage daily quotas, match thresholds, and non-circumvention rules for automated submissions"
      />

      <div className="max-w-4xl w-full mx-auto p-6 space-y-6">
        {/* Compliance Notice */}
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl flex items-center gap-3 shadow-lg">
          <ShieldCheck className="w-6 h-6 text-emerald-400 shrink-0" />
          <div className="text-xs text-slate-300">
            <span className="font-bold text-white block">Strict Non-Circumvention Policy:</span>
            Auto-apply runs only for platforms with verified partner/API submission capabilities (Greenhouse, Lever, Mock ATS).
            Platforms requiring user presence (LinkedIn, Naukri, Indeed, Unstop) return <code className="text-sky-400">EXTERNAL_APPLICATION_REQUIRED</code>.
          </div>
        </div>

        {savedSuccess && (
          <div className="p-4 bg-emerald-500/15 border border-emerald-500/30 rounded-xl flex items-center gap-3 text-emerald-300 text-sm">
            <CheckCircle2 className="w-5 h-5 shrink-0" />
            <span>Auto-apply policy successfully updated.</span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-500/15 border border-rose-500/30 rounded-xl flex items-center gap-3 text-rose-300 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-400" />
              <h3 className="font-bold text-white text-base">Execution Policy Controls</h3>
            </div>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-lg shadow-sky-500/20 transition-all"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Policy'}
            </button>
          </div>

          {/* Master Enable */}
          <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 flex items-center justify-between">
            <div>
              <span className="font-semibold text-white text-sm block">Master Auto-Apply Engine</span>
              <span className="text-xs text-slate-400">Allow autonomous queue submission worker to process eligible requisitions.</span>
            </div>
            <button
              type="button"
              onClick={() => setEnabled(!enabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                enabled ? 'bg-sky-500' : 'bg-slate-700'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Score Threshold & Quotas */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Minimum Match Score for Auto-Apply (%): {minScore}%
              </label>
              <input
                type="range"
                min="70"
                max="98"
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                className="w-full accent-sky-500 mt-2"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Global Daily Application Limit
              </label>
              <input
                type="number"
                value={dailyLimit}
                onChange={(e) => setDailyLimit(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Per-Platform Daily Limit
              </label>
              <input
                type="number"
                value={perSourceLimit}
                onChange={(e) => setPerSourceLimit(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Per-Company Limit
              </label>
              <input
                type="number"
                value={perCompanyLimit}
                onChange={(e) => setPerCompanyLimit(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>
          </div>

          {/* Guardrail Checkboxes */}
          <div className="pt-4 border-t border-slate-800 space-y-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={requireComplete}
                onChange={(e) => setRequireComplete(e.target.checked)}
                className="w-4 h-4 rounded text-sky-500"
              />
              <div>
                <span className="text-xs font-semibold text-white block">Require Complete Candidate Profile</span>
                <span className="text-[11px] text-slate-400">Never submit applications with blank mandatory candidate fields.</span>
              </div>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={duplicateProtection}
                onChange={(e) => setDuplicateProtection(e.target.checked)}
                className="w-4 h-4 rounded text-sky-500"
              />
              <div>
                <span className="text-xs font-semibold text-white block">Idempotent Duplicate Protection</span>
                <span className="text-[11px] text-slate-400">Prevent multiple submissions to identical requisitions across sources.</span>
              </div>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
