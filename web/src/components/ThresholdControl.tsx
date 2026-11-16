import React, { useEffect, useState } from 'react';
import { Sliders, Eye, Palette } from 'lucide-react';
import { useUIStore } from '../store/uiStore';

export const ThresholdControl: React.FC = () => {
  const { threshold, setThreshold, opacity, setOpacity, colorRamp, setColorRamp } = useUIStore();
  const [localThreshold, setLocalThreshold] = useState(threshold);

  // Debounce threshold update to store (250 ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setThreshold(localThreshold);
    }, 250);
    return () => clearTimeout(timer);
  }, [localThreshold, setThreshold]);

  return (
    <div className="space-y-4">
      {/* Risk Threshold Slider */}
      <div>
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="flex items-center gap-1.5 text-slate-300 font-medium">
            <Sliders className="w-3.5 h-3.5 text-emerald-400" />
            Risk Threshold
          </span>
          <span className="font-mono text-emerald-400 font-bold bg-emerald-500/10 px-1.5 py-0.5 rounded text-[11px]">
            {(localThreshold * 100).toFixed(0)}%
          </span>
        </div>
        <input
          type="range"
          min="0.05"
          max="0.95"
          step="0.05"
          value={localThreshold}
          onChange={(e) => setLocalThreshold(parseFloat(e.target.value))}
          className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
        />
        <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
          <span>5% (Sensitive)</span>
          <span>50%</span>
          <span>95% (High Conf)</span>
        </div>
      </div>

      {/* Heatmap Opacity Slider */}
      <div>
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="flex items-center gap-1.5 text-slate-300 font-medium">
            <Eye className="w-3.5 h-3.5 text-sky-400" />
            Overlay Opacity
          </span>
          <span className="font-mono text-sky-400 font-bold bg-sky-500/10 px-1.5 py-0.5 rounded text-[11px]">
            {(opacity * 100).toFixed(0)}%
          </span>
        </div>
        <input
          type="range"
          min="0.1"
          max="1.0"
          step="0.05"
          value={opacity}
          onChange={(e) => setOpacity(parseFloat(e.target.value))}
          className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
        />
      </div>

      {/* Color Ramp Selector */}
      <div>
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="flex items-center gap-1.5 text-slate-300 font-medium">
            <Palette className="w-3.5 h-3.5 text-amber-400" />
            Color Palette
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <button
            onClick={() => setColorRamp('risk')}
            className={`px-2.5 py-1.5 rounded-lg border flex items-center justify-center gap-1.5 transition-all ${
              colorRamp === 'risk'
                ? 'bg-emerald-500/15 border-emerald-500/50 text-white font-medium shadow-sm'
                : 'bg-slate-900/60 border-white/5 text-slate-400 hover:text-white'
            }`}
          >
            <span className="w-2.5 h-2.5 rounded-full bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500" />
            Perceptual Risk
          </button>
          <button
            onClick={() => setColorRamp('colorblind')}
            className={`px-2.5 py-1.5 rounded-lg border flex items-center justify-center gap-1.5 transition-all ${
              colorRamp === 'colorblind'
                ? 'bg-sky-500/15 border-sky-500/50 text-white font-medium shadow-sm'
                : 'bg-slate-900/60 border-white/5 text-slate-400 hover:text-white'
            }`}
          >
            <span className="w-2.5 h-2.5 rounded-full bg-gradient-to-r from-blue-700 via-teal-400 to-yellow-300" />
            Colorblind Safe
          </button>
        </div>
      </div>
    </div>
  );
};

