import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useUIStore } from './store/uiStore';
import {
  fetchScenes,
  fetchTimeline,
  fetchLatestResults,
  fetchAnalytics,
  fetchZonesGeoJson,
  fetchHealth,
} from './api/client';
import { Header } from './components/Header';
import { MapView } from './components/MapView';
import { SceneList } from './components/SceneList';
import { AnalyticsPanel } from './components/AnalyticsPanel';
import { TimelineSlider } from './components/TimelineSlider';
import { InferenceModal } from './components/InferenceModal';
import { AboutModal } from './components/AboutModal';
import { AddFarmModal } from './components/AddFarmModal';
import { Skeleton } from './components/Skeleton';
import { EmptyState } from './components/EmptyState';
import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen, RefreshCw } from 'lucide-react';

export const App: React.FC = () => {
  const {
    fieldId,
    setFieldId,
    sceneId,
    setSceneId,
    threshold,
    playing,
    setPlaying,
    setSelectedZoneId,
    sidebarOpen,
    setSidebarOpen,
    rightPanelOpen,
    setRightPanelOpen,
    isAddFarmModalOpen,
    setIsAddFarmModalOpen,
    setTargetLocation,
  } = useUIStore();

  const [isInferenceModalOpen, setIsInferenceModalOpen] = useState(false);
  const [isAboutModalOpen, setIsAboutModalOpen] = useState(false);
  const [targetModalSceneId, setTargetModalSceneId] = useState<string | null>(null);

  // 1. Health check
  const { data: healthData } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 30000,
  });

  // 2. Fetch scenes for field
  const {
    data: scenes = [],
    isLoading: scenesLoading,
    refetch: refetchScenes,
  } = useQuery({
    queryKey: ['scenes', fieldId],
    queryFn: () => fetchScenes(fieldId),
  });

  // Set default selected scene on initial load: select the latest acquisition!
  useEffect(() => {
    if (scenes.length > 0 && !sceneId) {
      setSceneId(scenes[scenes.length - 1].id);
    }
  }, [scenes, sceneId, setSceneId]);

  // Find active scene object
  const activeScene = scenes.find((s) => s.id === sceneId) || null;

  // 3. Fetch Timeline Points for Field
  const { data: timelineData, refetch: refetchTimeline } = useQuery({
    queryKey: ['timeline', fieldId, threshold],
    queryFn: () => fetchTimeline(fieldId, threshold),
    enabled: Boolean(fieldId),
  });

  // 4. Fetch Results, Analytics & Zones for Active Scene
  const { data: latestResults, refetch: refetchResults } = useQuery({
    queryKey: ['results', sceneId],
    queryFn: () => fetchLatestResults(sceneId!),
    enabled: Boolean(sceneId),
  });

  const {
    data: analyticsData,
    isLoading: analyticsLoading,
    refetch: refetchAnalytics,
  } = useQuery({
    queryKey: ['analytics', sceneId, threshold],
    queryFn: () => fetchAnalytics(sceneId!, threshold),
    enabled: Boolean(sceneId),
  });

  const { data: zonesGeoJson, refetch: refetchZones } = useQuery({
    queryKey: ['zones', sceneId, threshold],
    queryFn: () => fetchZonesGeoJson(sceneId!, threshold),
    enabled: Boolean(sceneId),
  });

  // Map of which scenes already have results
  const [hasResultsMap, setHasResultsMap] = useState<Record<string, boolean>>({});
  useEffect(() => {
    if (scenes.length > 0) {
      const checkResults = async () => {
        const map: Record<string, boolean> = {};
        for (const s of scenes) {
          try {
            const res = await fetchLatestResults(s.id);
            map[s.id] = Boolean(res);
          } catch {
            map[s.id] = false;
          }
        }
        setHasResultsMap(map);
      };
      checkResults();
    }
  }, [scenes, latestResults]);

  const handleOpenInference = (targetId?: string) => {
    setTargetModalSceneId(targetId || sceneId);
    setIsInferenceModalOpen(true);
  };

  const handleInferenceSuccess = () => {
    refetchResults();
    refetchAnalytics();
    refetchZones();
    refetchTimeline();
    refetchScenes();
  };

  const handleSelectZone = (zoneId: number, coords?: [number, number]) => {
    setSelectedZoneId(zoneId);
  };

  const handleFarmCreated = (newField: any) => {
    setFieldId(newField.id);
    setSceneId(null);
    setTargetLocation([newField.lon, newField.lat]);
    refetchScenes();
    refetchTimeline();
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0b0f17] text-slate-100">
      {/* Top Bar */}
      <Header
        onOpenInferenceModal={() => handleOpenInference()}
        onOpenAboutModal={() => setIsAboutModalOpen(true)}
        onOpenAddFarmModal={() => setIsAddFarmModalOpen(true)}
        systemHealth={healthData}
      />

      {/* Main Workspace Body */}
      <div className="flex-1 relative flex overflow-hidden">
        {/* Left Panel: Scenes & Acquisitions */}
        <div
          className={`glass-panel border-r border-white/10 flex flex-col transition-all duration-300 z-20 shrink-0 ${
            sidebarOpen ? 'w-80' : 'w-0 -translate-x-full overflow-hidden'
          }`}
        >
          <div className="p-4 border-b border-white/10 flex items-center justify-between">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-white">Acquisitions</h2>
              <p className="text-[10px] text-slate-400 font-mono">Multi-temporal HSI cubes</p>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => refetchScenes()}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
                title="Refresh scenes"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
                title="Collapse sidebar"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="p-3 flex-1 overflow-y-auto">
            {scenesLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : scenes.length > 0 ? (
              <SceneList
                scenes={scenes}
                selectedSceneId={sceneId}
                onSelectScene={(id) => setSceneId(id)}
                onRunInference={(id) => handleOpenInference(id)}
                hasResultsMap={hasResultsMap}
              />
            ) : (
              <EmptyState
                title="No Scenes Registered"
                description="Initialize synthetic cubes or upload a GeoTIFF raster to begin."
                actionLabel="Generate Scenes"
                onAction={() => handleOpenInference()}
              />
            )}
          </div>
        </div>

        {/* Left Panel Floating Expand Button */}
        {!sidebarOpen && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="absolute top-4 left-4 z-20 p-2.5 glass-panel rounded-xl text-slate-300 hover:text-white border border-white/10 shadow-2xl transition-all"
            title="Expand sidebar"
          >
            <PanelLeftOpen className="w-4 h-4" />
          </button>
        )}

        {/* Center: 3D Map View (Deck.gl + MapLibre) */}
        <div className="flex-1 relative h-full">
          <MapView
            scene={activeScene}
            zonesGeoJson={zonesGeoJson}
            gcps={[]}
            onSelectZone={handleSelectZone}
          />

          {/* Bottom Floating Timeline Slider */}
          <div className="absolute bottom-5 left-1/2 transform -translate-x-1/2 z-20 w-[94%] max-w-4xl">
            <TimelineSlider
              points={timelineData?.points || []}
              currentSceneId={sceneId}
              onSelectScene={(id) => setSceneId(id)}
              playing={playing}
              onTogglePlay={() => setPlaying(!playing)}
            />
          </div>
        </div>

        {/* Right Panel: Analytics & Insights */}
        <div
          className={`glass-panel border-l border-white/10 flex flex-col transition-all duration-300 z-20 shrink-0 ${
            rightPanelOpen ? 'w-96' : 'w-0 translate-x-full overflow-hidden'
          }`}
        >
          <div className="p-4 border-b border-white/10 flex items-center justify-between">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-white">Forecasting Analytics</h2>
              <p className="text-[10px] text-slate-400 font-mono">
                {activeScene ? `${activeScene.acres} acres surveyed` : 'Select scene'}
              </p>
            </div>
            <button
              onClick={() => setRightPanelOpen(false)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
              title="Collapse analytics"
            >
              <PanelRightClose className="w-4 h-4" />
            </button>
          </div>

          <div className="p-4 flex-1 overflow-y-auto">
            {analyticsLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-32 w-full" />
              </div>
            ) : analyticsData ? (
              <AnalyticsPanel
                analytics={analyticsData}
                zonesGeoJson={zonesGeoJson}
                onSelectZone={handleSelectZone}
              />
            ) : (
              <EmptyState
                title="Inference Required"
                description="Run the 3D-CNN + ViT model on this acquisition to compute disease risk."
                actionLabel="Run Inference"
                onAction={() => handleOpenInference()}
              />
            )}
          </div>
        </div>

        {/* Right Panel Floating Expand Button */}
        {!rightPanelOpen && (
          <button
            onClick={() => setRightPanelOpen(true)}
            className="absolute top-4 right-16 z-20 p-2.5 glass-panel rounded-xl text-slate-300 hover:text-white border border-white/10 shadow-2xl transition-all"
            title="Expand analytics"
          >
            <PanelRightOpen className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Modals */}
      <InferenceModal
        isOpen={isInferenceModalOpen}
        onClose={() => setIsInferenceModalOpen(false)}
        sceneId={targetModalSceneId || sceneId}
        onJobSuccess={handleInferenceSuccess}
      />

      <AboutModal
        isOpen={isAboutModalOpen}
        onClose={() => setIsAboutModalOpen(false)}
      />

      <AddFarmModal
        isOpen={isAddFarmModalOpen}
        onClose={() => setIsAddFarmModalOpen(false)}
        onFarmCreated={handleFarmCreated}
      />
    </div>
  );
};

