'use client';

import React from 'react';
import { Bell, Sparkles, User, ExternalLink } from 'lucide-react';
import Link from 'next/link';

interface HeaderProps {
  title: string;
  subtitle?: string;
  actionButton?: React.ReactNode;
}

export function Header({ title, subtitle, actionButton }: HeaderProps) {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-10 px-8 py-4 flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-4">
        {actionButton}

        <Link
          href="/chat"
          className="flex items-center gap-2 bg-gradient-to-r from-sky-500 to-indigo-600 text-white text-xs font-semibold px-3.5 py-2 rounded-lg shadow-sm hover:opacity-95 transition-opacity"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Ask Assistant</span>
        </Link>

        {/* User Avatar Pill */}
        <div className="flex items-center gap-3 pl-2 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center text-slate-700 font-bold text-xs">
            AM
          </div>
          <div className="hidden md:block text-left text-xs">
            <div className="font-semibold text-slate-800">Alex Mercer</div>
            <div className="text-slate-400">Senior AI Engineer</div>
          </div>
        </div>
      </div>
    </header>
  );
}
