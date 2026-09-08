'use client';

import React, { useEffect, useState } from 'react';
import { Header } from '@/components/Header';
import {
  Settings,
  Cpu,
  ShieldCheck,
  Save,
  CheckCircle2,
  Sliders,
  DollarSign,
  Briefcase,
  Layers,
} from 'lucide-react';
import { api } from '@/lib/api';

export default function SettingsPage() {
  const [aiConfig, setAiConfig] = useState<any>(null);
  const [targetRoles, setTargetRoles] = useState('');
  const [desiredLocations, setDesiredLocations] = useState('');
  const [minSalary, setMinSalary] = useState(0);
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [connectors, setConnectors] = useState<any[]>([]);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    try {
      const [connRes, userRes, aiRes] = await Promise.all([
        api.getConnectors().catch(() => []),
        api.getMe().catch(() => null),
        api.getAIConfig().catch(() => null),
      ]);
      setConnectors(Array.isArray(connRes) ? connRes : (connRes as any)?.data || []);
      if (aiRes) setAiConfig(aiRes);
      if (userRes && userRes.job_preferences && userRes.job_preferences.length > 0) {
        const pref = userRes.job_preferences[0];
        setTargetRoles((pref.desired_titles || []).join(', '));
        setDesiredLocations((pref.desired_locations || []).join(', '));
        setMinSalary(pref.min_base_salary || 0);
        setRemoteOnly(Array.isArray(pref.remote_types) && pref.remote_types.includes('REMOTE'));
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  }

  async function handleSave() {
    try {
      await api.updatePreferences({
        desired_titles: targetRoles.split(',').map((s) => s.trim()),
        desired_locations: desiredLocations.split(',').map((s) => s.trim()),
        remote_types: remoteOnly ? ['REMOTE'] : ['REMOTE', 'HYBRID'],
        min_base_salary: Number(minSalary),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: any) {
      alert(`Error saving preferences: ${err.message}`);
    }
  }

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Settings & System Configuration"
        subtitle="AI model routing, job preferences, and integration compliance controls"
      />

      <div className="p-8 space-y-8 max-w-5xl w-full mx-auto">
        {/* Quick Settings Navigation Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <a
            href="/settings/job-preferences"
            className="p-4 bg-white rounded-xl border border-slate-200 hover:border-sky-500 shadow-xs transition-all flex flex-col items-center text-center"
          >
            <Briefcase className="w-5 h-5 text-sky-500 mb-1.5" />
            <span className="text-xs font-bold text-slate-900">Job Preferences</span>
            <span className="text-[10px] text-slate-500 mt-0.5">Target roles & salaries</span>
          </a>
          <a
            href="/settings/auto-apply"
            className="p-4 bg-white rounded-xl border border-slate-200 hover:border-amber-500 shadow-xs transition-all flex flex-col items-center text-center"
          >
            <Sliders className="w-5 h-5 text-amber-500 mb-1.5" />
            <span className="text-xs font-bold text-slate-900">Auto-Apply Policy</span>
            <span className="text-[10px] text-slate-500 mt-0.5">Quotas & guardrails</span>
          </a>
          <a
            href="/settings/ai"
            className="p-4 bg-white rounded-xl border border-slate-200 hover:border-indigo-500 shadow-xs transition-all flex flex-col items-center text-center"
          >
            <Cpu className="w-5 h-5 text-indigo-500 mb-1.5" />
            <span className="text-xs font-bold text-slate-900">AI Engine</span>
            <span className="text-[10px] text-slate-500 mt-0.5">Gemini + OpenRouter</span>
          </a>
          <a
            href="/system/status"
            className="p-4 bg-white rounded-xl border border-slate-200 hover:border-emerald-500 shadow-xs transition-all flex flex-col items-center text-center"
          >
            <ShieldCheck className="w-5 h-5 text-emerald-500 mb-1.5" />
            <span className="text-xs font-bold text-slate-900">System Status</span>
            <span className="text-[10px] text-slate-500 mt-0.5">Real-time health</span>
          </a>
        </div>

        {saved && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Preferences saved and synchronized successfully!</span>
          </div>
        )}

        {/* AI Provider Architecture Card (Non-selectable, Canonical Dual Provider) */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-sky-500" />
                AI Provider Architecture
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Autonomous dual-engine routing: Google Gemini operates as Primary with automatic fallback to OpenRouter.
              </p>
            </div>
            <a
              href="/settings/ai"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 rounded-lg border border-sky-200 transition-colors w-fit"
            >
              <span>Configure Credentials</span>
              <span aria-hidden="true">&rarr;</span>
            </a>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Primary Provider Card */}
            <div className="p-4 rounded-xl border-2 border-emerald-100 bg-gradient-to-br from-emerald-50/30 to-white space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider bg-emerald-600 text-white rounded-full">
                    Primary Provider
                  </span>
                  <span className="text-xs font-bold text-slate-900">Google Gemini</span>
                </div>
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  {aiConfig?.primary_status || 'Active'}
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Direct integration with Gemini 1.5 Flash for high-speed, cost-efficient resume intelligence and tailored application drafting.
              </p>
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span>Model: <code className="text-emerald-800 font-mono font-medium">{aiConfig?.primary_model || 'gemini-1.5-flash'}</code></span>
                <span>Role: Primary Engine</span>
              </div>
            </div>

            {/* Fallback Provider Card */}
            <div className="p-4 rounded-xl border-2 border-amber-100 bg-gradient-to-br from-amber-50/30 to-white space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider bg-amber-600 text-white rounded-full">
                    Fallback Provider
                  </span>
                  <span className="text-xs font-bold text-slate-900">OpenRouter</span>
                </div>
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-sky-700 bg-sky-50 px-2 py-0.5 rounded-full border border-sky-200">
                  <CheckCircle2 className="w-3 h-3 text-sky-600" />
                  {aiConfig?.fallback_status || 'Hot Standby'}
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Unified model gateway automatically engaged if Gemini reaches rate limits (429), timeouts, or upstream network interruptions.
              </p>
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span>Model: <code className="text-amber-800 font-mono font-medium">{aiConfig?.fallback_model || 'google/gemini-flash-1.5'}</code></span>
                <span>Role: Automatic Fallback</span>
              </div>
            </div>
          </div>

          {/* Autonomous Routing Banner */}
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2 text-slate-700">
              <span className="font-bold text-slate-900">Routing Policy:</span>
              <span className="font-mono text-sky-700 font-semibold bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                Gemini &rarr; OpenRouter
              </span>
              <span className="text-slate-500 text-[11px]">Automatic failover. No manual switching required.</span>
            </div>
            <div className="text-[11px] text-slate-500">
              Active: <strong className="text-slate-800">{aiConfig?.active_display || 'Gemini (Primary)'}</strong>
            </div>
          </div>
        </div>

        {/* Job Matching Preferences */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Sliders className="w-4 h-4 text-indigo-500" />
            Job Search & Match Preferences
          </h3>

          <div className="space-y-4 text-xs">
            <div>
              <label className="font-bold text-slate-700 block mb-1">Target Role Titles (Comma-separated)</label>
              <input
                type="text"
                value={targetRoles}
                onChange={(e) => setTargetRoles(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-900"
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 block mb-1">Preferred Locations</label>
              <input
                type="text"
                value={desiredLocations}
                onChange={(e) => setDesiredLocations(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-900"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Minimum Base Salary (USD / year)</label>
                <input
                  type="number"
                  value={minSalary}
                  onChange={(e) => setMinSalary(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-900"
                />
              </div>

              <div className="flex items-center gap-3 pt-6">
                <input
                  type="checkbox"
                  id="remoteOnly"
                  checked={remoteOnly}
                  onChange={(e) => setRemoteOnly(e.target.checked)}
                  className="w-4 h-4 text-sky-600 rounded"
                />
                <label htmlFor="remoteOnly" className="font-semibold text-slate-700 cursor-pointer">
                  Prioritize 100% Remote Opportunities
                </label>
              </div>
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              onClick={handleSave}
              className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold px-5 py-2.5 rounded-xl shadow-sm transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Save Preferences</span>
            </button>
          </div>
        </div>

        {/* Authorized Connectors Compliance Table */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                Integration & Connector Capability Matrix
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Strict compliance rules protecting against anti-bot circumvention and unauthorized submissions.
              </p>
            </div>
          </div>

          <div className="border border-slate-200 rounded-xl overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-bold border-b border-slate-200">
                <tr>
                  <th className="p-3">Source Name</th>
                  <th className="p-3">Connector Capability Status</th>
                  <th className="p-3">Compliance Guarantee</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {connectors.map((c, i) => (
                  <tr key={i} className="hover:bg-slate-50/50">
                    <td className="p-3 font-bold text-slate-900">{c.name}</td>
                    <td className="p-3">
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                          c.capability_status === 'SUPPORTED_AUTO_APPLY'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : c.capability_status === 'SUPPORTED_JOB_DISCOVERY_ONLY'
                            ? 'bg-sky-50 text-sky-700 border-sky-200'
                            : 'bg-amber-50 text-amber-700 border-amber-200'
                        }`}
                      >
                        {c.capability_status}
                      </span>
                    </td>
                    <td className="p-3 text-slate-500">{c.compliance_notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
