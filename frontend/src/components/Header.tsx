'use client';

import React from 'react';

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

        {/* User Avatar Pill */}
        <UserPill />
      </div>
    </header>
  );
}

import Link from 'next/link';
import { LogIn, LogOut } from 'lucide-react';

function UserPill() {
  const [user, setUser] = React.useState<{ full_name?: string; headline?: string } | null>(null);
  const [authenticated, setAuthenticated] = React.useState<boolean>(false);
  const [loading, setLoading] = React.useState<boolean>(true);

  React.useEffect(() => {
    let isMounted = true;
    import('@/lib/api').then(({ api, getAuthToken, clearAuthToken }) => {
      const token = getAuthToken();
      if (!token) {
        if (isMounted) {
          setAuthenticated(false);
          setLoading(false);
        }
        return;
      }

      api.getMe()
        .then((u) => {
          if (isMounted && u) {
            setUser({
              full_name: u.full_name || 'Candidate',
              headline: u.profile?.headline || 'Job Seeker',
            });
            setAuthenticated(true);
          }
        })
        .catch(() => {
          if (isMounted) {
            clearAuthToken();
            setAuthenticated(false);
            setUser(null);
          }
        })
        .finally(() => {
          if (isMounted) setLoading(false);
        });
    });
    return () => {
      isMounted = false;
    };
  }, []);

  if (loading) {
    return <div className="w-8 h-8 rounded-full bg-slate-100 animate-pulse border border-slate-200"></div>;
  }

  if (!authenticated) {
    return (
      <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
        <Link
          href="/login"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-sm transition-colors cursor-pointer"
        >
          <LogIn className="w-3.5 h-3.5" />
          <span>Sign In</span>
        </Link>
      </div>
    );
  }

  const name = user?.full_name || 'Candidate';
  const headline = user?.headline || 'Active Profile';
  const initials = name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('') || 'CA';

  return (
    <div className="flex items-center gap-3 pl-2 border-l border-slate-200">
      <div className="w-8 h-8 rounded-full bg-sky-100 border border-sky-300 flex items-center justify-center text-sky-800 font-bold text-xs">
        {initials}
      </div>
      <div className="hidden md:block text-left text-xs">
        <div className="font-semibold text-slate-800">{name}</div>
        <div className="text-slate-400">{headline}</div>
      </div>
      <button
        onClick={() => {
          import('@/lib/api').then(({ clearAuthToken }) => {
            clearAuthToken();
            window.location.href = '/login';
          });
        }}
        title="Sign Out"
        className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-slate-100 transition-colors cursor-pointer"
      >
        <LogOut className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
