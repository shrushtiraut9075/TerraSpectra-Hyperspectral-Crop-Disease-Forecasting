import React from 'react';
import { TerraSpectraIcon } from './Logo';

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionLabel,
  onAction,
  className = ''
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center glass-panel rounded-xl border border-white/5 ${className}`}>
      <div className="relative mb-4">
        <div className="absolute -inset-4 bg-emerald-500/10 rounded-full blur-xl pointer-events-none" />
        <TerraSpectraIcon size={52} className="opacity-75" />
      </div>
      <h3 className="text-base font-semibold text-white mb-1.5">{title}</h3>
      <p className="text-xs text-slate-400 max-w-xs mb-5 leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-semibold rounded-lg shadow-lg shadow-emerald-500/20 transition-all duration-200 hover:scale-105 active:scale-95"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};

