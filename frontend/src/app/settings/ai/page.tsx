'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { apiClient } from '@/lib/api';
import { AIConfigInfo, AIConnectionTestResult } from '@/types';
import {
  Cpu,
  ShieldCheck,
  Save,
  CheckCircle2,
  AlertCircle,
  Activity,
  Zap,
  Lock,
  RefreshCw,
  ArrowRight,
  Server,
  KeyRound
} from 'lucide-react';

export default function AISettingsPage() {
  const [config, setConfig] = useState<AIConfigInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<AIConnectionTestResult | null>(null);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Gemini Primary States
  const [geminiApiKey, setGeminiApiKey] = useState('');
  const [geminiModel, setGeminiModel] = useState('gemini-1.5-flash');

  // OpenRouter Fallback States
  const [omnirouteBaseUrl, setOmnirouteBaseUrl] = useState('https://openrouter.ai/api/v1');
  const [omnirouteApiKey, setOmnirouteApiKey] = useState('');
  const [omnirouteModel, setOmnirouteModel] = useState('google/gemini-flash-1.5');

  // Gateway Controls
  const [timeoutSec, setTimeoutSec] = useState(30);
  const [maxRetries, setMaxRetries] = useState(3);

  useEffect(() => {
    loadAIConfig();
  }, []);

  async function loadAIConfig() {
    setLoading(true);
    try {
      const data = await apiClient.getAIConfig();
      setConfig(data);
      if (data.primary_model) setGeminiModel(data.primary_model);
      if (data.fallback_model) setOmnirouteModel(data.fallback_model);
      if (data.omniroute_base_url) setOmnirouteBaseUrl(data.omniroute_base_url);
      if (data.timeout_seconds) setTimeoutSec(data.timeout_seconds);
      if (data.max_retries) setMaxRetries(data.max_retries);
    } catch (err: any) {
      console.error('Failed to load AI config:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const updated = await apiClient.updateAIConfig({
        gemini_api_key: geminiApiKey ? geminiApiKey : undefined,
        gemini_model: geminiModel,
        omniroute_base_url: omnirouteBaseUrl,
        omniroute_api_key: omnirouteApiKey ? omnirouteApiKey : undefined,
        omniroute_model: omnirouteModel,
        timeout_seconds: Number(timeoutSec),
        max_retries: Number(maxRetries)
      });
      setConfig(updated);
      setGeminiApiKey('');
      setOmnirouteApiKey('');
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3500);
    } catch (err: any) {
      setError(err.message || 'Failed to update AI configuration');
    } finally {
      setSaving(false);
    }
  }

  async function handleTestConnection() {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await apiClient.testAIConnection();
      setTestResult(result);
    } catch (err: any) {
      setTestResult({
        status: 'UNAVAILABLE',
        provider: 'gemini',
        message: err.message || 'Connection test failed.',
        gemini_status: 'UNAVAILABLE',
        gemini_message: err.message,
        omniroute_status: 'UNAVAILABLE',
        omniroute_message: err.message
      });
    } finally {
      setTesting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 p-8 text-center text-slate-400 flex items-center justify-center min-h-[500px]">
        <div className="animate-spin w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full mb-2"></div>
        <span className="ml-3">Loading AI settings...</span>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-slate-950 text-slate-100 min-h-screen">
      <Header
        title="AI Provider & Resilience Architecture"
        subtitle="Canonical dual-engine setup: Google Gemini Primary + OmniRoute Automatic Fallback"
      />

      <div className="max-w-4xl w-full mx-auto p-6 space-y-6">
        {/* Secrets Security Alert */}
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl flex items-center gap-3 shadow-lg">
          <Lock className="w-5 h-5 text-sky-400 shrink-0" />
          <div className="text-xs text-slate-300">
            <span className="font-bold text-white block">Secrets Security & Zero Fabrication:</span>
            API keys are masked upon saving and stored securely. In production, if both Gemini and OmniRoute are unreachable, a controlled exception is raised with zero fabricated AI data.
          </div>
        </div>

        {savedSuccess && (
          <div className="p-4 bg-emerald-500/15 border border-emerald-500/30 rounded-xl flex items-center gap-3 text-emerald-300 text-sm">
            <CheckCircle2 className="w-5 h-5 shrink-0" />
            <span>AI configuration saved successfully. Routing updated to Gemini &rarr; OmniRoute.</span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-500/15 border border-rose-500/30 rounded-xl flex items-center gap-3 text-rose-300 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* AI Provider Architecture Summary Card */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <Cpu className="w-5 h-5 text-sky-400" />
                <h3 className="font-bold text-white text-base">AI Provider Architecture</h3>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Routing is fully autonomous: Google Gemini handles all primary tasks, switching to OmniRoute automatically on 429 quota limits or upstream latency.
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={testing}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-semibold rounded-lg flex items-center gap-1.5 border border-slate-700 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${testing ? 'animate-spin' : ''}`} />
                {testing ? 'Testing...' : 'Test Connection'}
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-1.5 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-lg shadow-sky-500/20 transition-colors"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving...' : 'Save Config'}
              </button>
            </div>
          </div>

          {/* Provider Badges */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
            <div className="p-4 bg-slate-850/60 border border-sky-900/40 rounded-xl flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider bg-sky-600 text-white rounded">
                    Primary
                  </span>
                  <span className="text-sm font-bold text-white">Google Gemini</span>
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Active Model: <code className="text-sky-300 font-mono">{config?.primary_model || geminiModel}</code>
                </div>
              </div>
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
                config?.primary_configured || config?.primary_status === 'AVAILABLE'
                  ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                  : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
              }`}>
                {config?.primary_status || 'Available'}
              </span>
            </div>

            <div className="p-4 bg-slate-850/60 border border-amber-900/40 rounded-xl flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider bg-amber-600 text-white rounded">
                    Fallback
                  </span>
                  <span className="text-sm font-bold text-white">OmniRoute</span>
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Fallback Model: <code className="text-amber-300 font-mono">{config?.fallback_model || omnirouteModel}</code>
                </div>
              </div>
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
                config?.fallback_configured || config?.fallback_status === 'READY'
                  ? 'bg-sky-500/15 text-sky-300 border-sky-500/30'
                  : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
              }`}>
                {config?.fallback_status || 'Ready'}
              </span>
            </div>
          </div>

          <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl flex items-center justify-between text-xs text-slate-300">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-sky-400" />
              <span><strong>Routing:</strong> Automatic (Gemini &rarr; OmniRoute). No manual switching required.</span>
            </div>
            <span className="text-slate-400 text-[11px]">Active: <strong className="text-white">{config?.active_display || 'Gemini (Primary)'}</strong></span>
          </div>
        </div>

        {/* Live Test Results Modal / Banner */}
        {testResult && (
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-sky-400" />
                <h4 className="font-bold text-white text-sm">Dual-Provider Diagnostic Results</h4>
              </div>
              <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded uppercase ${
                testResult.status === 'CONNECTED'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
              }`}>
                Overall: {testResult.status}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* Gemini Test Card */}
              <div className={`p-4 rounded-xl border text-xs space-y-1.5 ${
                testResult.gemini_status === 'CONNECTED'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
                  : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
              }`}>
                <div className="flex items-center justify-between font-bold">
                  <span>Primary: Google Gemini</span>
                  <span>{testResult.gemini_status || 'TESTED'}</span>
                </div>
                <div className="text-[11px] opacity-90">{testResult.gemini_message || 'Verification complete'}</div>
                {testResult.gemini_latency_ms !== undefined && testResult.gemini_latency_ms !== null && (
                  <div className="text-[10px] font-mono opacity-75 pt-1">Latency: {testResult.gemini_latency_ms}ms</div>
                )}
              </div>

              {/* OmniRoute Test Card */}
              <div className={`p-4 rounded-xl border text-xs space-y-1.5 ${
                testResult.omniroute_status === 'CONNECTED'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
                  : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
              }`}>
                <div className="flex items-center justify-between font-bold">
                  <span>Fallback: OpenRouter</span>
                  <span>{testResult.omniroute_status || 'TESTED'}</span>
                </div>
                <div className="text-[11px] opacity-90">{testResult.omniroute_message || 'Verification complete'}</div>
                {testResult.omniroute_latency_ms !== undefined && testResult.omniroute_latency_ms !== null && (
                  <div className="text-[10px] font-mono opacity-75 pt-1">Latency: {testResult.omniroute_latency_ms}ms</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* SECTION 1: Google Gemini (Primary) Configuration */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <KeyRound className="w-5 h-5 text-sky-400" />
            <div>
              <h3 className="font-bold text-white text-base">Primary Provider: Google Gemini</h3>
              <p className="text-xs text-slate-400">Configure direct Gemini API credentials and default model name.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Gemini API Key {config?.gemini_api_key_masked ? `(${config.gemini_api_key_masked})` : ''}
              </label>
              <input
                type="password"
                value={geminiApiKey}
                onChange={(e) => setGeminiApiKey(e.target.value)}
                placeholder={config?.primary_configured ? '•••••••••••••••• (Configured ✓)' : 'Enter Google Gemini API Key (AIzaSy...)'}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono placeholder:text-slate-500"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">Leave empty to keep existing key.</span>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Gemini Model</label>
              <input
                type="text"
                value={geminiModel}
                onChange={(e) => setGeminiModel(e.target.value)}
                placeholder="gemini-1.5-flash"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">Default: gemini-1.5-flash (multimodal, fast response).</span>
            </div>
          </div>
        </div>

        {/* SECTION 2: OpenRouter (Automatic Fallback) Configuration */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <Server className="w-5 h-5 text-amber-400" />
            <div>
              <h3 className="font-bold text-white text-base">Fallback Provider: OpenRouter</h3>
              <p className="text-xs text-slate-400">Configure OpenRouter endpoint, key, and default model for seamless fallback.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">OpenRouter Base URL</label>
              <input
                type="text"
                value={omnirouteBaseUrl}
                onChange={(e) => setOmnirouteBaseUrl(e.target.value)}
                placeholder="https://openrouter.ai/api/v1"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono placeholder:text-slate-500"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">Base URL of the OpenRouter gateway.</span>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                OpenRouter API Key {config?.omniroute_api_key_masked ? `(${config.omniroute_api_key_masked})` : ''}
              </label>
              <input
                type="password"
                value={omnirouteApiKey}
                onChange={(e) => setOmnirouteApiKey(e.target.value)}
                placeholder={config?.fallback_configured ? '•••••••••••••••• (Configured ✓)' : 'Enter OpenRouter API Key...'}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono placeholder:text-slate-500"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">Leave empty to keep existing key.</span>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">OpenRouter Model</label>
              <input
                type="text"
                value={omnirouteModel}
                onChange={(e) => setOmnirouteModel(e.target.value)}
                placeholder="google/gemini-flash-1.5"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">Model routed through OpenRouter fallback.</span>
            </div>
          </div>
        </div>

        {/* SECTION 3: Gateway & Resilience Controls */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <div>
              <h3 className="font-bold text-white text-base">Gateway & Resilience Controls</h3>
              <p className="text-xs text-slate-400">Timeouts and automatic retry parameters before triggering failover.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Gateway Timeout (Seconds)</label>
              <input
                type="number"
                value={timeoutSec}
                onChange={(e) => setTimeoutSec(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">Fallback triggers if primary request exceeds this duration.</span>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Max Retries</label>
              <input
                type="number"
                value={maxRetries}
                onChange={(e) => setMaxRetries(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">Exponential backoff retry attempts for transient errors.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
