import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  color?: 'blue' | 'indigo' | 'emerald' | 'amber' | 'purple' | 'slate';
  badge?: string;
}

const colorStyles = {
  blue: {
    iconBg: 'bg-sky-50 text-sky-600 border-sky-100',
    badge: 'bg-sky-50 text-sky-700 border-sky-200',
  },
  indigo: {
    iconBg: 'bg-indigo-50 text-indigo-600 border-indigo-100',
    badge: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  },
  emerald: {
    iconBg: 'bg-emerald-50 text-emerald-600 border-emerald-100',
    badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  },
  amber: {
    iconBg: 'bg-amber-50 text-amber-600 border-amber-100',
    badge: 'bg-amber-50 text-amber-700 border-amber-200',
  },
  purple: {
    iconBg: 'bg-purple-50 text-purple-600 border-purple-100',
    badge: 'bg-purple-50 text-purple-700 border-purple-200',
  },
  slate: {
    iconBg: 'bg-slate-50 text-slate-600 border-slate-200',
    badge: 'bg-slate-100 text-slate-700 border-slate-200',
  },
};

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color = 'blue',
  badge,
}: MetricCardProps) {
  const styles = colorStyles[color];

  return (
    <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</span>
        <div className={`w-9 h-9 rounded-xl border flex items-center justify-center ${styles.iconBg}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>

      <div className="mt-4 flex items-baseline gap-2">
        <span className="text-3xl font-bold tracking-tight text-slate-900">{value}</span>
        {badge && (
          <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${styles.badge}`}>
            {badge}
          </span>
        )}
      </div>

      {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
    </div>
  );
}
