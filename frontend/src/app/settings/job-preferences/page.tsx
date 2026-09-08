'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { apiClient } from '@/lib/api';
import { JobPreferencesConfig } from '@/types';
import {
  Briefcase,
  DollarSign,
  MapPin,
  Save,
  CheckCircle2,
  AlertCircle,
  Building,
  Sliders,
  Filter
} from 'lucide-react';

export default function JobPreferencesPage() {
  const [pref, setPref] = useState<JobPreferencesConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [titles, setTitles] = useState('');
  const [locations, setLocations] = useState('');
  const [remoteTypes, setRemoteTypes] = useState<string[]>(['REMOTE', 'HYBRID']);
  const [minSalary, setMinSalary] = useState<number | undefined>(140000);
  const [maxSalary, setMaxSalary] = useState<number | undefined>(220000);
  const [currency, setCurrency] = useState('USD');
  const [employmentTypes, setEmploymentTypes] = useState<string[]>(['FULL_TIME']);
  const [preferredIndustries, setPreferredIndustries] = useState('');
  const [excludedIndustries, setExcludedIndustries] = useState('');
  const [preferredCompanies, setPreferredCompanies] = useState('');
  const [blockedCompanies, setBlockedCompanies] = useState('');
  const [blockedKeywords, setBlockedKeywords] = useState('');
  const [minScore, setMinScore] = useState(65);
  const [freshnessDays, setFreshnessDays] = useState(30);

  useEffect(() => {
    loadPreferences();
  }, []);

  async function loadPreferences() {
    setLoading(true);
    try {
      const data = await apiClient.getJobPreferences();
      setPref(data);
      setTitles((data.desired_titles || []).join(', '));
      setLocations((data.desired_locations || []).join(', '));
      setRemoteTypes(data.remote_types || ['REMOTE']);
      setMinSalary(data.min_base_salary);
      setMaxSalary(data.max_base_salary);
      setCurrency(data.currency || 'USD');
      setEmploymentTypes(data.employment_types || ['FULL_TIME']);
      setPreferredIndustries((data.preferred_industries || []).join(', '));
      setExcludedIndustries((data.excluded_industries || []).join(', '));
      setPreferredCompanies((data.preferred_companies || []).join(', '));
      setBlockedCompanies((data.blocked_companies || []).join(', '));
      setBlockedKeywords((data.blocked_keywords || []).join(', '));
      setMinScore(data.minimum_match_score || 65);
      setFreshnessDays(data.job_freshness_days || 30);
    } catch (err: any) {
      console.error('Failed to load job preferences:', err);
    } finally {
      setLoading(false);
    }
  }

  function handleToggleRemote(type: string) {
    if (remoteTypes.includes(type)) {
      if (remoteTypes.length > 1) {
        setRemoteTypes(remoteTypes.filter((t) => t !== type));
      }
    } else {
      setRemoteTypes([...remoteTypes, type]);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const payload: Partial<JobPreferencesConfig> = {
        desired_titles: titles.split(',').map((s) => s.trim()).filter(Boolean),
        desired_locations: locations.split(',').map((s) => s.trim()).filter(Boolean),
        remote_types: remoteTypes,
        min_base_salary: minSalary ? Number(minSalary) : undefined,
        max_base_salary: maxSalary ? Number(maxSalary) : undefined,
        currency,
        employment_types: employmentTypes,
        preferred_industries: preferredIndustries.split(',').map((s) => s.trim()).filter(Boolean),
        excluded_industries: excludedIndustries.split(',').map((s) => s.trim()).filter(Boolean),
        preferred_companies: preferredCompanies.split(',').map((s) => s.trim()).filter(Boolean),
        blocked_companies: blockedCompanies.split(',').map((s) => s.trim()).filter(Boolean),
        blocked_keywords: blockedKeywords.split(',').map((s) => s.trim()).filter(Boolean),
        minimum_match_score: Number(minScore),
        job_freshness_days: Number(freshnessDays),
        target_industries: preferredIndustries.split(',').map((s) => s.trim()).filter(Boolean)
      };

      const updated = await apiClient.updateJobPreferences(payload);
      setPref(updated);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save job preferences');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 p-8 text-center text-slate-400 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full mb-2"></div>
        <span className="ml-3">Loading preferences...</span>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-slate-950 text-slate-100 min-h-screen">
      <Header
        title="Job Discovery & Matching Preferences"
        subtitle="Configure target roles, locations, compensation, and safety keyword filters"
      />

      <div className="max-w-4xl w-full mx-auto p-6 space-y-6">
        {savedSuccess && (
          <div className="p-4 bg-emerald-500/15 border border-emerald-500/30 rounded-xl flex items-center gap-3 text-emerald-300 text-sm">
            <CheckCircle2 className="w-5 h-5 shrink-0" />
            <span>Job discovery preferences saved successfully.</span>
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
              <Briefcase className="w-5 h-5 text-sky-400" />
              <h3 className="font-bold text-white text-base">Roles & Target Locations</h3>
            </div>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-lg shadow-sky-500/20 transition-all"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Preferences'}
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Target Roles (Comma-separated)
              </label>
              <input
                type="text"
                value={titles}
                onChange={(e) => setTitles(e.target.value)}
                placeholder="Senior Backend Engineer, Systems Architect, Lead Developer"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Preferred Locations (Comma-separated)
              </label>
              <input
                type="text"
                value={locations}
                onChange={(e) => setLocations(e.target.value)}
                placeholder="San Francisco, CA, New York, NY, Austin, TX"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-2">Work Arrangement</label>
              <div className="flex gap-3">
                {['REMOTE', 'HYBRID', 'ONSITE'].map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => handleToggleRemote(type)}
                    className={`px-4 py-2 rounded-xl text-xs font-semibold border transition-all ${
                      remoteTypes.includes(type)
                        ? 'bg-sky-500/20 border-sky-500 text-sky-300'
                        : 'bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700'
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Compensation & Scoring */}
          <div className="pt-4 border-t border-slate-800 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Minimum Base Salary ({currency})
              </label>
              <input
                type="number"
                value={minSalary || ''}
                onChange={(e) => setMinSalary(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Minimum AI Match Threshold (%): {minScore}%
              </label>
              <input
                type="range"
                min="50"
                max="95"
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                className="w-full accent-sky-500 mt-2"
              />
            </div>
          </div>

          {/* Company & Keyword Blocking */}
          <div className="pt-4 border-t border-slate-800 space-y-4">
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-indigo-400" />
              <h3 className="font-bold text-white text-base">Company & Keyword Filters</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">
                  Blocked Companies (Excluded from matching & auto-apply)
                </label>
                <input
                  type="text"
                  value={blockedCompanies}
                  onChange={(e) => setBlockedCompanies(e.target.value)}
                  placeholder="CompanyA, CompanyB"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">
                  Blocked Keywords (In job title or description)
                </label>
                <input
                  type="text"
                  value={blockedKeywords}
                  onChange={(e) => setBlockedKeywords(e.target.value)}
                  placeholder="contractor, unpaid, unpaid internship"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
