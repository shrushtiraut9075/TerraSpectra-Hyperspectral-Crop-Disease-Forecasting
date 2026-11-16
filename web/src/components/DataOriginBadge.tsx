import React from 'react';
import { ShieldAlert, Database, CheckCircle2 } from 'lucide-react';

interface DataOriginBadgeProps {
  origin?: 'synthetic' | 'public' | 'real';
  className?: string;
}

export const DataOriginBadge: React.FC<DataOriginBadgeProps> = ({
  origin = 'synthetic',
  className = ''
}) => {
  const configs = {
    synthetic: {
      label: 'SYNTHETIC DATA',
      sublabel: 'Physical Spectral Simulation',
      color: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      icon: ShieldAlert,
      tooltip: 'Plausible radiative spectral simulation for pre-symptomatic forecasting validation'
    },
    public: {
      label: 'PUBLIC BENCHMARK',
      sublabel: 'Indian Pines / Salinas',
      color: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
      icon: Database,
      tooltip: 'Standard public hyperspectral land-cover benchmark'
    },
    real: {
      label: 'REAL SATELLITE',
      sublabel: 'PRISMA / EnMAP',
      color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      icon: CheckCircle2,
      tooltip: 'Live on-orbit hyperspectral sensor data'
    }
  };

  const config = configs[origin];
  const Icon = config.icon;

  return (
    <div
      title={config.tooltip}
      className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full border text-xs font-mono font-medium backdrop-blur-md transition-all ${config.color} ${className}`}
    >
      <Icon className="w-3.5 h-3.5 animate-pulse" />
      <span className="font-bold tracking-wider">{config.label}</span>
      <span className="hidden sm:inline text-[10px] opacity-75">({config.sublabel})</span>
    </div>
  );
};

