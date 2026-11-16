import React from 'react';
import { Scene } from '../types';
import { Calendar, Layers, CheckCircle2, AlertCircle, Play } from 'lucide-react';

interface SceneListProps {
  scenes: Scene[];
  selectedSceneId: string | null;
  onSelectScene: (sceneId: string) => void;
  onRunInference: (sceneId: string) => void;
  hasResultsMap: Record<string, boolean>;
}

export const SceneList: React.FC<SceneListProps> = ({
  scenes,
  selectedSceneId,
  onSelectScene,
  onRunInference,
  hasResultsMap,
}) => {
  if (!scenes || scenes.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-slate-500 font-mono">
        No registered acquisitions found.
      </div>
    );
  }

  return (
    <div className="space-y-1.5 overflow-y-auto max-h-[380px] pr-1">
      {scenes.map((scene) => {
        const isSelected = scene.id === selectedSceneId;
        const hasResult = hasResultsMap[scene.id];
        const dateObj = new Date(scene.acquired_at);
        const dateStr = dateObj.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
        });

        return (
          <div
            key={scene.id}
            onClick={() => onSelectScene(scene.id)}
            className={`group p-3 rounded-xl border transition-all duration-200 cursor-pointer flex flex-col gap-2 ${
              isSelected
                ? 'bg-emerald-500/10 border-emerald-500/50 shadow-md shadow-emerald-500/5'
                : 'bg-slate-900/40 border-white/5 hover:bg-slate-800/40 hover:border-white/10'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className={`w-3.5 h-3.5 ${isSelected ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span className={`text-xs font-semibold ${isSelected ? 'text-white' : 'text-slate-200'}`}>
                  {dateStr}
                </span>
              </div>
              {hasResult ? (
                <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  <CheckCircle2 className="w-3 h-3" />
                  ANALYZED
                </span>
              ) : (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRunInference(scene.id);
                  }}
                  className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 px-2 py-0.5 rounded-full border border-amber-500/30 transition-colors"
                >
                  <Play className="w-2.5 h-2.5 fill-current" />
                  RUN
                </button>
              )}
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
              <span className="flex items-center gap-1">
                <Layers className="w-3 h-3 text-slate-500" />
                {scene.raster.bands} bands ({scene.raster.pixel_size_m}m/px)
              </span>
              <span>{scene.acres} acres</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

