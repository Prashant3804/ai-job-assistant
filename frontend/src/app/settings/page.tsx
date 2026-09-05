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
  const [provider, setProvider] = useState('mock');
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
      const [connRes, userRes] = await Promise.all([
        api.getConnectors().catch(() => []),
        api.getMe().catch(() => null),
      ]);
      setConnectors(Array.isArray(connRes) ? connRes : (connRes as any)?.data || []);
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
            <span className="text-xs font-bold text-slate-900">AI OmniRoute</span>
            <span className="text-[10px] text-slate-500 mt-0.5">Model gateway test</span>
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

        {/* AI Provider Config */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-sky-500" />
            AI Service Layer & Provider Routing
          </h3>
          <p className="text-xs text-slate-500">
            Select the underlying LLM provider for embeddings, structured JSON extraction, and chat intelligence.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 pt-2">
            {[
              { id: 'mock', name: 'Mock AI (Local)', desc: 'Zero API tokens, offline deterministic execution' },
              { id: 'openai', name: 'OpenAI (GPT-4o)', desc: 'text-embedding-3 + structured JSON' },
              { id: 'gemini', name: 'Google Gemini', desc: 'Gemini 1.5 Flash + Pro multimodal' },
              { id: 'anthropic', name: 'Anthropic Claude', desc: 'Claude 3.5 Sonnet advanced reasoning' },
            ].map((p) => (
              <div
                key={p.id}
                onClick={() => setProvider(p.id)}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  provider === p.id
                    ? 'border-sky-500 bg-sky-50/50 shadow-xs'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900">{p.name}</span>
                  {provider === p.id && <CheckCircle2 className="w-4 h-4 text-sky-600" />}
                </div>
                <p className="text-[11px] text-slate-500 mt-1 leading-snug">{p.desc}</p>
              </div>
            ))}
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
