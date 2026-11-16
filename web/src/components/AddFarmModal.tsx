import React, { useState } from 'react';
import { X, MapPin, Search, Sprout, Loader2, CheckCircle2, Globe } from 'lucide-react';
import { createField, searchLocations } from '../api/client';
import { FieldItem, LocationSearchResult } from '../types';

interface AddFarmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onFarmCreated: (field: FieldItem) => void;
}

export const AddFarmModal: React.FC<AddFarmModalProps> = ({ isOpen, onClose, onFarmCreated }) => {
  const [name, setName] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<LocationSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [lat, setLat] = useState<number>(18.2198); // Default Baramati / Pune belt
  const [lon, setLon] = useState<number>(74.4534);
  const [selectedPlaceName, setSelectedPlaceName] = useState('Baramati, Pune, Maharashtra');
  const [acres, setAcres] = useState<number>(250);
  const [cropType, setCropType] = useState('Sugarcane');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    if (query.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    try {
      const results = await searchLocations(query);
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const selectLocation = (result: LocationSearchResult) => {
    setLat(result.lat);
    setLon(result.lon);
    setSelectedPlaceName(result.name);
    setSearchResults([]);
    setSearchQuery('');
    if (!name) {
      const shortName = result.name.split(',')[0].trim();
      setName(`${shortName} ${cropType} Field`);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Please provide a name for this land/farm.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const newField = await createField({
        name: name.trim(),
        lat,
        lon,
        acres,
        crop_type: cropType,
      });
      onFarmCreated(newField);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to create farm');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fade-in">
      <div className="glass-panel w-full max-w-lg rounded-2xl border border-white/15 shadow-2xl p-6 relative max-h-[92vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-5">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-400">
              <Sprout className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Register Your Land / Farm
              </h2>
              <p className="text-xs text-slate-400">
                Search your village or enter coordinates for hyperspectral disease forecasting
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Location Search Bar */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
              <Search className="w-3.5 h-3.5 text-emerald-400" />
              Search Village / City / District
            </label>
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                placeholder="e.g., Baramati, Shirur, Satara, Amritsar, Nashik..."
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900/90 border border-white/15 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors pr-10"
              />
              {isSearching && (
                <div className="absolute right-3 top-3 text-slate-400 animate-spin">
                  <Loader2 className="w-4 h-4" />
                </div>
              )}
            </div>

            {/* Search Results Dropdown */}
            {searchResults.length > 0 && (
              <div className="mt-2 rounded-xl bg-slate-900 border border-white/15 shadow-2xl p-1.5 space-y-1 max-h-48 overflow-y-auto">
                {searchResults.map((res, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => selectLocation(res)}
                    className="w-full text-left px-3 py-2 rounded-lg hover:bg-white/10 text-xs text-slate-200 flex items-start gap-2 transition-colors"
                  >
                    <MapPin className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    <span className="line-clamp-2">{res.name}</span>
                  </button>
                ))}
              </div>
            )}

            {/* Current Selected Location Indicator */}
            {selectedPlaceName && (
              <div className="mt-2 px-3 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/25 flex items-center gap-2 text-xs text-emerald-300">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                <span className="truncate">{selectedPlaceName}</span>
              </div>
            )}
          </div>

          {/* Farm Name */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Farm / Parcel Name
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. My Village Sugarcane Land"
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900/90 border border-white/15 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
            />
          </div>

          {/* GPS Coordinates Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1 font-mono">
                Latitude (°N)
              </label>
              <input
                type="number"
                step="any"
                required
                value={lat}
                onChange={(e) => setLat(parseFloat(e.target.value))}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1 font-mono">
                Longitude (°E)
              </label>
              <input
                type="number"
                step="any"
                required
                value={lon}
                onChange={(e) => setLon(parseFloat(e.target.value))}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          {/* Crop Type & Acreage */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Crop Type
              </label>
              <select
                value={cropType}
                onChange={(e) => setCropType(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-white/15 text-xs font-semibold text-white focus:outline-none focus:border-emerald-500 cursor-pointer"
              >
                <option value="Sugarcane">Sugarcane</option>
                <option value="Wheat">Wheat</option>
                <option value="Cotton">Cotton</option>
                <option value="Soybean">Soybean</option>
                <option value="Grapes">Grapes (Vineyard)</option>
                <option value="Rice">Rice</option>
                <option value="Maize">Maize / Corn</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Acreage Size
              </label>
              <div className="flex gap-1.5">
                {[50, 100, 250, 500].map((val) => (
                  <button
                    key={val}
                    type="button"
                    onClick={() => setAcres(val)}
                    className={`flex-1 py-1.5 rounded-lg text-xs font-mono font-bold border transition-colors ${
                      acres === val
                        ? 'bg-emerald-500 border-emerald-400 text-slate-950'
                        : 'bg-slate-900 border-white/10 text-slate-300 hover:bg-slate-800'
                    }`}
                  >
                    {val}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Submit Action */}
          <div className="pt-3 flex items-center justify-end gap-3 border-t border-white/10">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold text-xs flex items-center gap-2 shadow-lg shadow-emerald-500/20 disabled:opacity-50 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating Hyperspectral Cube...
                </>
              ) : (
                <>
                  <Globe className="w-4 h-4" />
                  Register & Monitor Land
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

