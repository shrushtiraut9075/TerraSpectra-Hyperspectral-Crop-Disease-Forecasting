import React, { useEffect } from 'react';
import { Play, Pause, ChevronLeft, ChevronRight, Clock } from 'lucide-react';
import { TimelinePoint } from '../types';
import { TrendSparkline } from './TrendSparkline';

interface TimelineSliderProps {
  points: TimelinePoint[];
  currentSceneId: string | null;
  onSelectScene: (sceneId: string) => void;
  playing: boolean;
  onTogglePlay: () => void;
}

export const TimelineSlider: React.FC<TimelineSliderProps> = ({
  points,
  currentSceneId,
  onSelectScene,
  playing,
  onTogglePlay,
}) => {
  const currentIndex = points.findIndex((p) => p.scene_id === currentSceneId);
  const safeIndex = currentIndex >= 0 ? currentIndex : 0;

  // Playback loop (1.2s per step per frontend-spec.md §7)
  useEffect(() => {
    if (!playing || points.length === 0) return;

    const timer = setInterval(() => {
      const nextIdx = (safeIndex + 1) % points.length;
      onSelectScene(points[nextIdx].scene_id);
    }, 1200);

    return () => clearInterval(timer);
  }, [playing, safeIndex, points, onSelectScene]);

  // Keyboard navigation (ArrowLeft / ArrowRight)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        const prevIdx = Math.max(0, safeIndex - 1);
        onSelectScene(points[prevIdx].scene_id);
      } else if (e.key === 'ArrowRight') {
        const nextIdx = Math.min(points.length - 1, safeIndex + 1);
        onSelectScene(points[nextIdx].scene_id);
      } else if (e.key === ' ') {
        e.preventDefault();
        onTogglePlay();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [safeIndex, points, onSelectScene, onTogglePlay]);

  if (!points || points.length === 0) return null;

  return (
    <div className="glass-panel p-3 rounded-2xl border border-white/10 shadow-2xl flex flex-col md:flex-row items-center gap-4">
      {/* Controls & Current Date */}
      <div className="flex items-center gap-3 shrink-0">
        <button
          onClick={onTogglePlay}
          className="p-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-lg shadow-emerald-500/20 transition-all hover:scale-105 active:scale-95"
          title={playing ? 'Pause timeline' : 'Play timeline across dates'}
        >
          {playing ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current" />}
        </button>

        <div className="flex items-center gap-1">
          <button
            onClick={() => onSelectScene(points[Math.max(0, safeIndex - 1)].scene_id)}
            disabled={safeIndex === 0}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 disabled:opacity-30 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => onSelectScene(points[Math.min(points.length - 1, safeIndex + 1)].scene_id)}
            disabled={safeIndex === points.length - 1}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 disabled:opacity-30 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <div className="text-left font-mono">
          <div className="text-[10px] text-slate-400 flex items-center gap-1">
            <Clock className="w-3 h-3 text-emerald-400" />
            Acquisition Date
          </div>
          <div className="text-xs font-bold text-white">
            {new Date(points[safeIndex]?.acquired_at || Date.now()).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })}
          </div>
        </div>
      </div>

      {/* Date Steps Progress Track */}
      <div className="flex-1 w-full flex flex-col gap-1.5">
        <div className="flex items-center justify-between gap-1 w-full">
          {points.map((p, idx) => {
            const isSelected = idx === safeIndex;
            const isPast = idx < safeIndex;
            return (
              <button
                key={p.scene_id}
                onClick={() => onSelectScene(p.scene_id)}
                className="group flex-1 flex flex-col items-center py-1 transition-all"
              >
                <div
                  className={`w-full h-1.5 rounded-full transition-all duration-300 ${
                    isSelected
                      ? 'bg-emerald-400 shadow-sm shadow-emerald-400'
                      : isPast
                      ? 'bg-slate-700'
                      : 'bg-slate-800'
                  }`}
                />
                <span
                  className={`text-[9px] font-mono mt-1 transition-colors ${
                    isSelected ? 'text-emerald-400 font-bold' : 'text-slate-500 group-hover:text-slate-300'
                  }`}
                >
                  T{idx < 10 ? `0${idx}` : idx}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Trend Sparkline (Acreage at Risk Trajectory) */}
      <div className="w-full md:w-48 shrink-0">
        <TrendSparkline points={points} currentSceneId={currentSceneId} />
      </div>
    </div>
  );
};

