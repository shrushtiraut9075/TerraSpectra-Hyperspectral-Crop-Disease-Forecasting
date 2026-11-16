import { create } from 'zustand';

export interface UIState {
  fieldId: string;
  sceneId: string | null;
  threshold: number; // 0..1
  opacity: number; // 0..1
  layers: {
    risk: boolean;
    zones: boolean;
    gcps: boolean;
    farmBoundary: boolean;
    terrain: boolean;
  };
  basemap: 'satellite' | 'dark' | 'streets';
  colorRamp: 'risk' | 'colorblind';
  selectedZoneId: number | null;
  playing: boolean;
  activeJobId: string | null;
  jobProgress: number;
  jobStatus: string | null;
  sidebarOpen: boolean;
  rightPanelOpen: boolean;
  targetLocation: [number, number] | null;
  isAddFarmModalOpen: boolean;

  setFieldId: (id: string) => void;
  setSceneId: (id: string | null) => void;
  setThreshold: (val: number) => void;
  setOpacity: (val: number) => void;
  toggleLayer: (layer: keyof UIState['layers']) => void;
  setBasemap: (map: 'satellite' | 'dark' | 'streets') => void;
  setColorRamp: (ramp: 'risk' | 'colorblind') => void;
  setSelectedZoneId: (id: number | null) => void;
  setPlaying: (playing: boolean) => void;
  setActiveJob: (jobId: string | null, status?: string, progress?: number) => void;
  setJobProgress: (progress: number, status?: string) => void;
  setSidebarOpen: (open: boolean) => void;
  setRightPanelOpen: (open: boolean) => void;
  setTargetLocation: (loc: [number, number] | null) => void;
  setIsAddFarmModalOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  fieldId: 'farm-a',
  sceneId: null,
  threshold: 0.5,
  opacity: 0.85,
  layers: {
    risk: true,
    zones: true,
    gcps: true,
    farmBoundary: true,
    terrain: true,
  },
  basemap: 'satellite',
  colorRamp: 'risk',
  selectedZoneId: null,
  playing: false,
  activeJobId: null,
  jobProgress: 0,
  jobStatus: null,
  sidebarOpen: true,
  rightPanelOpen: true,
  targetLocation: null,
  isAddFarmModalOpen: false,

  setFieldId: (id) => set({ fieldId: id }),
  setSceneId: (id) => set({ sceneId: id, selectedZoneId: null }),
  setThreshold: (val) => set({ threshold: val }),
  setOpacity: (val) => set({ opacity: val }),
  toggleLayer: (layer) =>
    set((state) => ({
      layers: { ...state.layers, [layer]: !state.layers[layer] },
    })),
  setBasemap: (map) => set({ basemap: map }),
  setColorRamp: (ramp) => set({ colorRamp: ramp }),
  setSelectedZoneId: (id) => set({ selectedZoneId: id }),
  setPlaying: (playing) => set({ playing }),
  setActiveJob: (jobId, status = 'queued', progress = 0) =>
    set({ activeJobId: jobId, jobStatus: status, jobProgress: progress }),
  setJobProgress: (progress, status) =>
    set((state) => ({
      jobProgress: progress,
      jobStatus: status || state.jobStatus,
    })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setRightPanelOpen: (open) => set({ rightPanelOpen: open }),
  setTargetLocation: (loc) => set({ targetLocation: loc }),
  setIsAddFarmModalOpen: (open) => set({ isAddFarmModalOpen: open }),
}));

