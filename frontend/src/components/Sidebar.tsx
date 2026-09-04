'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  BotMessageSquare,
  FileText,
  Search,
  Sparkles,
  Briefcase,
  Zap,
  Mail,
  Calendar,
  BarChart3,
  Settings,
  ShieldCheck,
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'AI Chat', href: '/chat', icon: BotMessageSquare, badge: 'AI' },
  { name: 'My Resume', href: '/resume', icon: FileText },
  { name: 'Find Jobs', href: '/jobs', icon: Search },
  { name: 'Recommended Jobs', href: '/recommended', icon: Sparkles, highlight: true },
  { name: 'Match History', href: '/matches', icon: BarChart3 },
  { name: 'Applications', href: '/applications', icon: Briefcase },
  { name: 'Auto-Apply', href: '/auto-apply', icon: Zap, badge: 'AUTO', highlight: true },
  { name: 'Mailbox & Recruiter', href: '/mailbox', icon: Mail, badge: 'OAUTH' },
  { name: 'Interviews', href: '/interviews', icon: Calendar },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Onboarding', href: '/onboarding', icon: Sparkles, badge: 'SETUP' },
  { name: 'Integrations', href: '/settings/integrations', icon: ShieldCheck, badge: 'PROD' },
  { name: 'System Status', href: '/system/status', icon: ShieldCheck },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 h-screen sticky top-0 border-r border-slate-800">
      {/* Brand Header */}
      <div className="p-5 flex items-center gap-3 border-b border-slate-800">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-sky-500/20 font-bold text-lg">
          AI
        </div>
        <div>
          <h1 className="font-bold text-white tracking-tight leading-tight">Job Assistant</h1>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-xs text-slate-400 font-medium">Compliance Active</span>
          </div>
        </div>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold px-3 mb-2">
          Platform Workspace
        </div>
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-sky-600/15 text-sky-400 border border-sky-500/30'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-sky-400' : 'text-slate-400'}`} />
                <span>{item.name}</span>
              </div>
              {item.badge && (
                <span className="bg-sky-500/20 text-sky-300 border border-sky-500/30 text-[10px] font-bold px-1.5 py-0.5 rounded">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Compliance / Safety badge */}
      <div className="p-3 m-3 rounded-xl bg-slate-800/60 border border-slate-700/60">
        <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Safe Connector Policy</span>
        </div>
        <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
          Non-circumvention rules strictly enforced. Official authorized APIs only.
        </p>
      </div>
    </aside>
  );
}
