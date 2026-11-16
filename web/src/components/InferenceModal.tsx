import React, { useState, useEffect } from 'react';
import { X, Cpu, Clock, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react';
import { startInferenceJob, fetchJobStatus } from '../api/client';
import { useUIStore } from '../store/uiStore';
import { TerraSpectraIcon } from './Logo';

interface InferenceModalProps {
  isOpen: boolean;
  onClose: () => void;
  sceneId: string | null;
  onJobSuccess: () => void;
}

export const InferenceModal: React.FC<InferenceModalProps> = ({
  isOpen,
  onClose,
  sceneId,
  onJobSuccess,
}) => {
  const [model, setModel] = useState('hybrid-v1');
  const [horizonDays, setHorizonDays] = useState(21);
  const [tileSize, setTileSize] = useState(256);
  const [overlap, setOverlap] = useState(32);
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState(0);
  const [statusText, setStatusText] = useState<string>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Poll job status
  useEffect(() => {
    if (!jobId || statusText === 'succeeded' || statusText === 'failed') return;

    const interval = setInterval(async () => {
      try {
        const job = await fetchJobStatus(jobId);
        setJobProgress(job.progress);
        setStatusText(job.status);

        if (job.status === 'succeeded') {
          clearInterval(interval);
          setLoading(false);
          setTimeout(() => {
            onJobSuccess();
            onClose();
          }, 800);
        } else if (job.status === 'failed') {
          clearInterval(interval);
          setLoading(false);
          setErrorMessage(job.error || 'Inference execution failed');
        }
      } catch (err: any) {
        console.error('Job polling error:', err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [jobId, statusText, onJobSuccess, onClose]);

  if (!isOpen) return null;

  const handleStartInference = async () => {
    if (!sceneId) return;
    setLoading(true);
    setErrorMessage(null);
    setStatusText('queued');
    try {
      const res = await startInferenceJob(sceneId, {
        model,
        horizon_days: horizonDays,
        tile_size: tileSize,
        overlap: overlap,
      });
      setJobId(res.job_id);
      setStatusText(res.status);
    } catch (err: any) {
      setLoading(false);
      setErrorMessage(err.message || 'Failed to submit inference job');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="glass-panel w-full max-w-lg p-6 rounded-2xl border border-white/10 shadow-2xl relative">
        <button
          onClick={onClose}
          disabled={loading && statusText === 'running'}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors disabled:opacity-40"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <TerraSpectraIcon size={38} />
          <div>
            <h2 className="text-base font-bold text-white">Execute Tiled Inference</h2>
            <p className="text-xs text-slate-400 font-mono">
              3D-CNN + ViT Hyperspectral Chemical Anomaly Pipeline
            </p>
          </div>
        </div>

        {errorMessage && (
          <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {!loading ? (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-emerald-400" />
                Deep Learning Model
              </label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900/80 border border-white/10 rounded-xl text-xs text-white focus:outline-none focus:border-emerald-500/50"
              >
                <option value="hybrid-v1">Hybrid 3D-CNN + Vision Transformer (Target)</option>
                <option value="cnn3d-v1">3D-CNN Spatial-Spectral Stem Only</option>
                <option value="cnn2d-v1">2D-CNN Spatial Baseline</option>
                <option value="mlp-v1">Spectral-only MLP Baseline</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-sky-400" />
                  Forecasting Horizon
                </label>
                <select
                  value={horizonDays}
                  onChange={(e) => setHorizonDays(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-900/80 border border-white/10 rounded-xl text-xs text-white focus:outline-none focus:border-emerald-500/50 font-mono"
                >
                  <option value={14}>14 Days (2 Weeks)</option>
                  <option value={21}>21 Days (3 Weeks, Standard)</option>
                  <option value={28}>28 Days (4 Weeks)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Tile & Overlap (px)
                </label>
                <select
                  value={`${tileSize}-${overlap}`}
                  onChange={(e) => {
                    const [ts, ov] = e.target.value.split('-').map(Number);
                    setTileSize(ts);
                    setOverlap(ov);
                  }}
                  className="w-full px-3 py-2 bg-slate-900/80 border border-white/10 rounded-xl text-xs text-white focus:outline-none focus:border-emerald-500/50 font-mono"
                >
                  <option value="256-32">256 × 256 (32px Hann blend)</option>
                  <option value="128-16">128 × 128 (16px Hann blend)</option>
                </select>
              </div>
            </div>

            <div className="pt-4 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-white/5 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleStartInference}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 text-xs font-bold shadow-lg shadow-emerald-500/20 transition-all hover:scale-105 active:scale-95"
              >
                Start Tiled Inference
              </button>
            </div>
          </div>
        ) : (
          <div className="py-6 flex flex-col items-center justify-center space-y-4 text-center">
            <div className="relative">
              {statusText === 'succeeded' ? (
                <CheckCircle2 className="w-12 h-12 text-emerald-400 animate-in zoom-in duration-300" />
              ) : (
                <Loader2 className="w-12 h-12 text-emerald-400 animate-spin" />
              )}
            </div>

            <div>
              <p className="text-sm font-semibold text-white capitalize">{statusText}...</p>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                {statusText === 'running'
                  ? `Streaming spatial tiles with 2D Hann feathering`
                  : `Preparing model and tensor buffers`}
              </p>
            </div>

            <div className="w-full max-w-xs space-y-1.5">
              <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-emerald-400 to-teal-400 h-2.5 rounded-full transition-all duration-300"
                  style={{ width: `${Math.round(jobProgress * 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                <span>Progress</span>
                <span>{Math.round(jobProgress * 100)}%</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

