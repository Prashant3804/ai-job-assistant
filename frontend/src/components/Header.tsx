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

function UserPill() {
  const [user, setUser] = React.useState<{ full_name?: string; headline?: string } | null>(null);

  React.useEffect(() => {
    let isMounted = true;
    import('@/lib/api').then(({ api }) => {
      api.getMe()
        .then((u) => {
          if (isMounted && u) {
            setUser({
              full_name: u.full_name || 'Candidate',
              headline: u.profile?.headline || 'Job Seeker',
            });
          }
        })
        .catch(() => {
          if (isMounted) {
            setUser({ full_name: 'Candidate', headline: 'Active Profile' });
          }
        });
    });
    return () => {
      isMounted = false;
    };
  }, []);

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
      <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center text-slate-700 font-bold text-xs">
        {initials}
      </div>
      <div className="hidden md:block text-left text-xs">
        <div className="font-semibold text-slate-800">{name}</div>
        <div className="text-slate-400">{headline}</div>
      </div>
    </div>
  );
}
