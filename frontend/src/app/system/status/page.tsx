'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { apiClient } from '@/lib/api';
import { SystemStatusInfo } from '@/types';
import {
  Activity,
  Server,
  Database,
  Mail,
  Cpu,
  Layers,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Clock,
  ShieldCheck
} from 'lucide-react';

export default function SystemStatusPage() {
  const [status, setStatus] = useState<SystemStatusInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadStatus();
  }, []);

  async function loadStatus() {
    setRefreshing(true);
    try {
      const data = await apiClient.getSystemStatus();
      setStatus(data);
    } catch (err: any) {
      console.error('Failed to load system status:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  function renderStatusBadge(statusVal: string) {
    switch (statusVal) {
      case 'HEALTHY':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" /> HEALTHY
          </span>
        );
      case 'DEGRADED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
            <AlertTriangle className="w-3.5 h-3.5" /> DEGRADED
          </span>
        );
      case 'NOT_CONFIGURED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-slate-800 text-slate-400 border border-slate-700">
            <Clock className="w-3.5 h-3.5" /> NOT CONFIGURED
          </span>
        );
      case 'AUTH_REQUIRED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
            <ShieldCheck className="w-3.5 h-3.5" /> AUTH REQUIRED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30">
            <XCircle className="w-3.5 h-3.5" /> DOWN
          </span>
        );
    }
  }

  if (loading) {
    return (
      <div className="flex-1 p-8 text-center text-slate-400 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full mb-2"></div>
        <span className="ml-3">Checking production system telemetry...</span>
      </div>
    );
  }

  const components = status
    ? [
        { key: 'database', comp: status.database, icon: Database },
        { key: 'omniroute', comp: status.omniroute, icon: Cpu },
        { key: 'gmail', comp: status.gmail, icon: Mail },
        { key: 'outlook', comp: status.outlook, icon: Mail },
        { key: 'job_connectors', comp: status.job_connectors, icon: Layers },
        { key: 'application_queue', comp: status.application_queue, icon: Server },
        { key: 'workers', comp: status.workers, icon: Activity },
        { key: 'ai_service', comp: status.ai_service, icon: Cpu },
      ]
    : [];

  return (
    <div className="flex-1 flex flex-col bg-slate-950 text-slate-100 min-h-screen">
      <Header
        title="Production System Status & Telemetry"
        subtitle="Real-time health telemetry across Database, AI Gateway, Mailbox, and Platform Connectors"
      />

      <div className="max-w-6xl w-full mx-auto p-6 space-y-6">
        {/* Top Status Header */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 flex items-center justify-between shadow-xl">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-bold text-white">System Status: {status?.overall_status}</h2>
                {renderStatusBadge(status?.overall_status || 'HEALTHY')}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Environment: <span className="font-mono text-slate-300">{status?.environment}</span> | Version: <span className="font-mono text-slate-300">v{status?.version}</span>
              </p>
            </div>
          </div>
          <button
            onClick={loadStatus}
            disabled={refreshing}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-semibold rounded-xl flex items-center gap-2 border border-slate-700 shadow-md"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh Telemetry
          </button>
        </div>

        {/* Components Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {components.map(({ key, comp, icon: Icon }) => (
            <div
              key={key}
              className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-sky-400">
                      <Icon className="w-4 h-4" />
                    </div>
                    <h3 className="font-bold text-white text-sm">{comp.name}</h3>
                  </div>
                  {renderStatusBadge(comp.status)}
                </div>
                <p className="text-xs text-slate-300 leading-relaxed mb-3">
                  {comp.details || 'Component active and operating normally.'}
                </p>
              </div>
              <div className="text-[11px] text-slate-500 border-t border-slate-800/80 pt-2 flex items-center justify-between">
                <span>Slug: {comp.slug}</span>
                <span>Checked: {new Date(comp.last_checked).toLocaleTimeString()}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
