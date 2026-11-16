import React from 'react';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showText?: boolean;
  className?: string;
}

export const TerraSpectraIcon: React.FC<{ size?: number; className?: string }> = ({
  size = 36,
  className = ''
}) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 transition-transform duration-300 hover:scale-105 ${className}`}
    >
      <defs>
        {/* Hyperspectral Gradient: Visible -> RedEdge -> NIR -> SWIR */}
        <linearGradient id="spectral-band-1" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#10b981" />
          <stop offset="100%" stopColor="#047857" />
        </linearGradient>
        <linearGradient id="spectral-band-2" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#84cc16" />
          <stop offset="100%" stopColor="#10b981" />
        </linearGradient>
        <linearGradient id="spectral-band-3" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#f59e0b" />
          <stop offset="100%" stopColor="#eab308" />
        </linearGradient>
        <linearGradient id="spectral-band-4" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#ef4444" />
          <stop offset="100%" stopColor="#f97316" />
        </linearGradient>
        <linearGradient id="orbital-ring" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.9" />
          <stop offset="50%" stopColor="#10b981" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#a855f7" stopOpacity="0.8" />
        </linearGradient>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Hexagonal Isometric Field Shield */}
      <polygon
        points="24,4 42,14 42,34 24,44 6,34 6,14"
        fill="#0b1324"
        stroke="#1e293b"
        strokeWidth="1.5"
      />

      {/* Layer 1: Soil & Healthy Base Terrain (Bottom Isometric Layer) */}
      <path
        d="M6,28 L24,38 L42,28 L42,34 L24,44 L6,34 Z"
        fill="url(#spectral-band-1)"
        opacity="0.85"
      />

      {/* Layer 2: Canopy & Red-Edge Transition Layer */}
      <path
        d="M8,22 L24,31 L40,22 L40,27 L24,36 L8,27 Z"
        fill="url(#spectral-band-2)"
        opacity="0.9"
      />

      {/* Layer 3: Early Spectral Anomaly Slice (Amber) */}
      <path
        d="M12,16 L24,23 L36,16 L36,20 L24,27 L12,20 Z"
        fill="url(#spectral-band-3)"
      />

      {/* Layer 4: SWIR / Severe Horizon Warning Crest */}
      <polygon
        points="24,7 34,13 24,19 14,13"
        fill="url(#spectral-band-4)"
        filter="url(#glow)"
      />

      {/* Satellite Sensor Focus Reticle / Orbital Ellipse */}
      <ellipse
        cx="24"
        cy="24"
        rx="20"
        ry="8"
        fill="none"
        stroke="url(#orbital-ring)"
        strokeWidth="1.2"
        strokeDasharray="3 2"
        transform="rotate(-25 24 24)"
      />

      {/* Sensor Target Node */}
      <circle cx="24" cy="19" r="1.5" fill="#ffffff" filter="url(#glow)" />
    </svg>
  );
};

export const Logo: React.FC<LogoProps> = ({
  size = 'md',
  showText = true,
  className = ''
}) => {
  const iconSizes = {
    sm: 28,
    md: 38,
    lg: 48,
    xl: 60
  };

  const textSizes = {
    sm: 'text-base',
    md: 'text-xl',
    lg: 'text-2xl',
    xl: 'text-3xl'
  };

  const subtitleSizes = {
    sm: 'text-[9px] tracking-widest',
    md: 'text-[10px] tracking-widest',
    lg: 'text-xs tracking-widest',
    xl: 'text-sm tracking-widest'
  };

  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      <TerraSpectraIcon size={iconSizes[size]} />
      {showText && (
        <div className="flex flex-col leading-none">
          <div className={`font-bold tracking-tight text-white flex items-center ${textSizes[size]}`}>
            <span>Terra</span>
            <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-amber-400 bg-clip-text text-transparent ml-0.5">
              Spectra
            </span>
          </div>
          <span className={`font-medium uppercase text-emerald-400/80 font-mono mt-1 ${subtitleSizes[size]}`}>
            Hyperspectral Forecasting
          </span>
        </div>
      )}
    </div>
  );
};

