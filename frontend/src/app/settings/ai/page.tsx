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
  RefreshCw
} from 'lucide-react';

export default function AISettingsPage() {
  const [config, setConfig] = useState<AIConfigInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<AIConnectionTestResult | null>(null);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [provider, setProvider] = useState('omniroute');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('gpt-4o-mini');
  const [timeoutSec, setTimeoutSec] = useState(30);

  useEffect(() => {
    loadAIConfig();
  }, []);

  async function loadAIConfig() {
    setLoading(true);
    try {
      const data = await apiClient.getAIConfig();
      setConfig(data);
      setProvider(data.provider);
      setModel(data.model);
      setTimeoutSec(data.timeout_seconds);
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
        provider,
        model,
        timeout_seconds: Number(timeoutSec),
        api_key: apiKey ? apiKey : undefined
      });
      setConfig(updated);
      setApiKey('');
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
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
        provider,
        message: err.message || 'Connection test failed.'
      });
    } finally {
      setTesting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 p-8 text-center text-slate-400 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full mb-2"></div>
        <span className="ml-3">Loading AI settings...</span>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-slate-950 text-slate-100 min-h-screen">
      <Header
        title="OmniRoute AI Gateway Configuration"
        subtitle="Configure LLM providers, model routes, and test live connection health"
      />

      <div className="max-w-4xl w-full mx-auto p-6 space-y-6">
        {/* Security Alert */}
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl flex items-center gap-3 shadow-lg">
          <Lock className="w-5 h-5 text-sky-400 shrink-0" />
          <div className="text-xs text-slate-300">
            <span className="font-bold text-white block">Secrets Security:</span>
            API keys are masked upon saving and stored securely. Secret values are never exposed to client-side bundles or logs.
          </div>
        </div>

        {savedSuccess && (
          <div className="p-4 bg-emerald-500/15 border border-emerald-500/30 rounded-xl flex items-center gap-3 text-emerald-300 text-sm">
            <CheckCircle2 className="w-5 h-5 shrink-0" />
            <span>AI configuration saved successfully.</span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-500/15 border border-rose-500/30 rounded-xl flex items-center gap-3 text-rose-300 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* AI Config Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="w-5 h-5 text-sky-400" />
              <h3 className="font-bold text-white text-base">Model Provider & Gateway Settings</h3>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={testing}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-semibold rounded-lg flex items-center gap-1.5 border border-slate-700"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${testing ? 'animate-spin' : ''}`} />
                {testing ? 'Testing...' : 'Test Connection'}
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-1.5 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-lg shadow-sky-500/20"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving...' : 'Save Config'}
              </button>
            </div>
          </div>

          {/* Test Connection Result Box */}
          {testResult && (
            <div
              className={`p-4 rounded-xl border flex items-center justify-between ${
                testResult.status === 'CONNECTED'
                  ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
                  : testResult.status === 'NOT_CONFIGURED'
                  ? 'bg-amber-500/15 border-amber-500/30 text-amber-300'
                  : 'bg-rose-500/15 border-rose-500/30 text-rose-300'
              }`}
            >
              <div className="flex items-center gap-3">
                <Activity className="w-5 h-5 shrink-0" />
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider">
                    Connection Status: {testResult.status}
                  </div>
                  <div className="text-xs mt-0.5">{testResult.message}</div>
                </div>
              </div>
              {testResult.latency_ms && (
                <span className="text-xs font-mono bg-slate-900/60 px-2 py-1 rounded">
                  {testResult.latency_ms}ms
                </span>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">AI Provider</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              >
                <option value="omniroute">OmniRoute (Unified Model Gateway)</option>
                <option value="openai">OpenAI (Direct API)</option>
                <option value="gemini">Google Gemini (Direct API)</option>
                <option value="mock">Deterministic Mock (Local Test Provider)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Model Route</label>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="gpt-4o-mini / gemini-1.5-pro"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                API Key {config?.api_key_masked ? `(${config.api_key_masked})` : ''}
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={config?.is_configured ? '•••••••••••••••• (Configured ✓)' : 'Enter API Key...'}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Gateway Timeout (Seconds)
              </label>
              <input
                type="number"
                value={timeoutSec}
                onChange={(e) => setTimeoutSec(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
