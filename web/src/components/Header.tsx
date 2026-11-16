import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Logo } from './Logo';
import { DataOriginBadge } from './DataOriginBadge';
import { useUIStore } from '../store/uiStore';
import { fetchFields, searchLocations } from '../api/client';
import { FieldItem, LocationSearchResult } from '../types';
import {
  Play,
  Layers,
  ChevronDown,
  Check,
  BookOpen,
  Search,
  Plus,
  MapPin,
  Loader2,
} from 'lucide-react';

interface HeaderProps {
  onOpenInferenceModal: () => void;
  onOpenAboutModal: () => void;
  onOpenAddFarmModal: () => void;
  systemHealth?: { status: string; gpu: boolean; model_loaded: boolean };
}

export const Header: React.FC<HeaderProps> = ({
  onOpenInferenceModal,
  onOpenAboutModal,
  onOpenAddFarmModal,
  systemHealth,
}) => {
  const { fieldId, setFieldId, layers, toggleLayer, basemap, setBasemap, setTargetLocation } =
    useUIStore();
  const [layerDropdownOpen, setLayerDropdownOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<LocationSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Fetch all registered fields / farms
  const { data: fields = [] } = useQuery({
    queryKey: ['fields'],
    queryFn: fetchFields,
    refetchInterval: 10000,
  });

  const handleSearch = async (val: string) => {
    setSearchQuery(val);
    if (val.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    try {
      const res = await searchLocations(val);
      setSearchResults(res);
    } catch {
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectLocation = (res: LocationSearchResult) => {
    setTargetLocation([res.lon, res.lat]);
    setSearchResults([]);
    setSearchQuery('');
  };

  return (
    <header className="h-16 px-4 md:px-5 glass-panel border-b border-white/10 flex items-center justify-between z-30 select-none gap-4">
      {/* Left: Brand Identity & Field Selector */}
      <div className="flex items-center gap-4 sm:gap-6 shrink-0">
        <Logo size="md" />

        <div className="hidden md:block h-6 w-px bg-white/10" />

        {/* Field Selector */}
        <div className="hidden sm:flex items-center gap-2">
          <span className="text-xs text-slate-400 font-medium">Field:</span>
          <select
            value={fieldId}
            onChange={(e) => setFieldId(e.target.value)}
            className="px-2.5 py-1 bg-slate-900/90 border border-white/15 rounded-lg text-xs font-semibold text-white focus:outline-none focus:border-emerald-500/50 cursor-pointer max-w-[220px] truncate"
          >
            {fields.map((f: FieldItem) => (
              <option key={f.id} value={f.id}>
                {f.name} ({f.acres} Acres)
              </option>
            ))}
          </select>

          {/* Add Farm Button */}
          <button
            onClick={onOpenAddFarmModal}
            className="px-2.5 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border border-emerald-500/40 text-xs font-semibold flex items-center gap-1 transition-all active:scale-95"
            title="Register your village land or farm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="hidden lg:inline">Add Land</span>
          </button>
        </div>
      </div>

      {/* Center: Location Search Bar */}
      <div className="relative flex items-center max-w-sm w-full mx-2">
        <div className="flex items-center gap-2 w-full px-3 py-1.5 rounded-xl bg-slate-900/90 border border-white/15 text-xs focus-within:border-emerald-500/60 shadow-inner transition-colors">
          <Search className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search village, town, or coordinates..."
            className="bg-transparent text-white placeholder-slate-500 focus:outline-none w-full text-xs"
          />
          {isSearching && <Loader2 className="w-3 h-3 text-slate-400 animate-spin shrink-0" />}
        </div>

        {/* Search Results Autocomplete Dropdown */}
        {searchResults.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-1.5 rounded-xl bg-slate-900 border border-white/20 shadow-2xl p-1.5 space-y-1 z-50 max-h-56 overflow-y-auto">
            {searchResults.map((res, idx) => (
              <button
                key={idx}
                onClick={() => handleSelectLocation(res)}
                className="w-full text-left px-3 py-2 rounded-lg hover:bg-white/10 text-xs text-slate-200 flex items-start gap-2 transition-colors"
              >
                <MapPin className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <div className="truncate">
                  <p className="font-semibold text-white truncate">{res.name.split(',')[0]}</p>
                  <p className="text-[10px] text-slate-400 truncate">{res.name}</p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right: Quick Controls & Actions */}
      <div className="flex items-center gap-2 shrink-0">
        <div className="hidden xl:block">
          <DataOriginBadge origin="synthetic" />
        </div>

        {/* Layer Toggles Menu */}
        <div className="relative">
          <button
            onClick={() => setLayerDropdownOpen(!layerDropdownOpen)}
            className="px-3 py-1.5 rounded-lg bg-slate-900/80 hover:bg-slate-800 border border-white/10 text-xs font-medium text-slate-200 flex items-center gap-1.5 transition-colors"
          >
            <Layers className="w-3.5 h-3.5 text-emerald-400" />
            <span className="hidden sm:inline">Layers</span>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </button>

          {layerDropdownOpen && (
            <div className="absolute right-0 mt-2 w-56 glass-panel rounded-xl shadow-2xl p-2 border border-white/10 space-y-1 z-50">
              <div className="text-[10px] font-mono uppercase text-slate-400 px-2 py-1 font-bold">
                Map Overlays
              </div>
              {[
                { key: 'risk', label: 'Disease Risk Heatmap' },
                { key: 'zones', label: 'Focal Risk Zones' },
                { key: 'gcps', label: 'Ground Control Points' },
                { key: 'farmBoundary', label: 'Field Boundary Grid' },
                { key: 'terrain', label: '3D Terrain & Pitch' },
              ].map(({ key, label }) => {
                const isActive = (layers as any)[key];
                return (
                  <button
                    key={key}
                    onClick={() => toggleLayer(key as any)}
                    className="w-full px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between text-left hover:bg-white/5 transition-colors"
                  >
                    <span className={isActive ? 'text-white font-medium' : 'text-slate-400'}>{label}</span>
                    <div
                      className={`w-4 h-4 rounded flex items-center justify-center border ${
                        isActive ? 'bg-emerald-500 border-emerald-400 text-slate-950' : 'border-slate-700'
                      }`}
                    >
                      {isActive && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                  </button>
                );
              })}

              <div className="text-[10px] font-mono uppercase text-slate-400 px-2 py-1 font-bold pt-2 border-t border-white/5">
                Basemap
              </div>
              {[
                { key: 'satellite', label: 'Satellite (ESRI)' },
                { key: 'dark', label: 'Dark Canvas' },
                { key: 'streets', label: 'OpenStreetMap' },
              ].map(({ key, label }) => {
                const isActive = basemap === key;
                return (
                  <button
                    key={key}
                    onClick={() => setBasemap(key as any)}
                    className="w-full px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between text-left hover:bg-white/5 transition-colors"
                  >
                    <span className={isActive ? 'text-white font-medium' : 'text-slate-400'}>{label}</span>
                    <div
                      className={`w-4 h-4 rounded-full flex items-center justify-center border ${
                        isActive ? 'bg-emerald-500 border-emerald-400 text-slate-950' : 'border-slate-700'
                      }`}
                    >
                      {isActive && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Documentation / Methodology */}
        <button
          onClick={onOpenAboutModal}
          className="p-2 rounded-lg bg-slate-900/80 hover:bg-slate-800 border border-white/10 text-slate-300 hover:text-white transition-colors"
          title="Methodology & Model Card"
        >
          <BookOpen className="w-4 h-4" />
        </button>

        {/* Run Inference CTA */}
        <button
          onClick={onOpenInferenceModal}
          className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 text-xs font-bold shadow-lg shadow-emerald-500/20 flex items-center gap-1.5 transition-all hover:scale-105 active:scale-95 shrink-0"
        >
          <Play className="w-3 h-3 fill-current" />
          <span className="hidden md:inline">Run Inference</span>
        </button>
      </div>
    </header>
  );
};


