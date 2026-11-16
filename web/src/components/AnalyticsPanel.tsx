import React, { useState } from 'react';
import { AnalyticsData, RiskZoneProperties } from '../types';
import { AnomalyChart } from './AnomalyChart';
import { RiskHistogram } from './RiskHistogram';
import { ThresholdControl } from './ThresholdControl';
import { AlertTriangle, ArrowUpDown, ChevronRight, MapPin, Sparkles } from 'lucide-react';
import { useUIStore } from '../store/uiStore';

interface AnalyticsPanelProps {
  analytics: AnalyticsData | null;
  zonesGeoJson: any | null;
  onSelectZone: (zoneId: number, coordinates?: [number, number]) => void;
  loading?: boolean;
}

export const AnalyticsPanel: React.FC<AnalyticsPanelProps> = ({
  analytics,
  zonesGeoJson,
  onSelectZone,
  loading = false,
}) => {
  const { selectedZoneId } = useUIStore();
  const [sortField, setSortField] = useState<'area_acres' | 'mean_risk'>('mean_risk');
  const [sortAsc, setSortAsc] = useState(false);

  if (!analytics) {
    return (
      <div className="p-6 text-center text-slate-400 text-xs">
        Select a scene and run inference to inspect detailed agricultural analytics.
      </div>
    );
  }

  // Extract zones properties from GeoJSON features
  const rawFeatures = zonesGeoJson?.features || [];
  const zonesList: { properties: RiskZoneProperties; coordinates: [number, number] }[] = rawFeatures.map(
    (f: any) => {
      // Find centroid coordinates for fly-to
      let center: [number, number] = [73.7, 18.5];
      if (f.geometry?.coordinates?.[0]?.[0]) {
        center = f.geometry.coordinates[0][0];
      }
      return {
        properties: f.properties,
        coordinates: center,
      };
    }
  );

  // Sort zones
  const sortedZones = [...zonesList].sort((a, b) => {
    const valA = a.properties[sortField] || 0;
    const valB = b.properties[sortField] || 0;
    return sortAsc ? valA - valB : valB - valA;
  });

  // Deterministic template-based natural language summary per frontend-spec.md §7
  const largestZone = zonesList.reduce<RiskZoneProperties | null>((max, curr) => {
    if (!max || curr.properties.area_acres > max.area_acres) return curr.properties;
    return max;
  }, null);

  const summarySentence =
    analytics.acres_at_risk > 0
      ? `${analytics.percent_at_risk}% of the field (${analytics.acres_at_risk} acres) exhibits chemical stress signatures ~3 weeks ahead of visible chlorosis.${
          largestZone
            ? ` Largest focal zone covers ${largestZone.area_acres} acres (mean risk: ${(
                largestZone.mean_risk * 100
              ).toFixed(0)}%).`
            : ''
        }`
      : `0.0% of the surveyed acreage exceeds the ${Math.round(
          analytics.threshold * 100
        )}% disease risk threshold. All crop sectors appear healthy.`;

  return (
    <div className="space-y-6 text-slate-200">
      {/* Top Headline Numbers */}
      <div className="grid grid-cols-2 gap-3">
        <div className="glass-panel p-4 rounded-xl border border-red-500/20 bg-gradient-to-br from-red-500/10 to-transparent">
          <div className="flex items-center gap-1.5 text-xs text-red-400 font-semibold mb-1">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>ACRES AT RISK</span>
          </div>
          <div className="text-3xl font-extrabold text-white font-mono tracking-tight">
            {analytics.acres_at_risk}
          </div>
          <div className="text-[11px] text-slate-400 font-mono mt-0.5">
            {analytics.percent_at_risk}% of {analytics.acres_total} acres
          </div>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-white/5">
          <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold mb-1">
            <MapPin className="w-3.5 h-3.5" />
            <span>RISK ZONES</span>
          </div>
          <div className="text-3xl font-extrabold text-white font-mono tracking-tight">
            {analytics.zones_count}
          </div>
          <div className="text-[11px] text-slate-400 font-mono mt-0.5">
            Isolated focal patches
          </div>
        </div>
      </div>

      {/* Template-based Exact Natural Language Summary */}
      <div className="glass-panel p-3.5 rounded-xl border border-emerald-500/20 bg-emerald-500/5 text-xs text-slate-300 leading-relaxed flex gap-2.5 items-start">
        <Sparkles className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
        <p className="font-normal">{summarySentence}</p>
      </div>

      {/* Threshold & Opacity Controls */}
      <div className="glass-panel p-4 rounded-xl border border-white/5">
        <ThresholdControl />
      </div>

      {/* Anomaly Spectral Breakdown Chart */}
      {analytics.anomalies && analytics.anomalies.length > 0 && (
        <div className="glass-panel p-4 rounded-xl border border-white/5">
          <AnomalyChart anomalies={analytics.anomalies} />
        </div>
      )}

      {/* Risk Histogram */}
      {analytics.risk_histogram && (
        <div className="glass-panel p-4 rounded-xl border border-white/5">
          <RiskHistogram histogram={analytics.risk_histogram} />
        </div>
      )}

      {/* Risk Zones Table */}
      <div className="glass-panel p-4 rounded-xl border border-white/5 space-y-3">
        <div className="flex items-center justify-between text-xs font-semibold">
          <span className="text-white">Identified Risk Zones</span>
          <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
            <span>Sort by:</span>
            <button
              onClick={() => {
                if (sortField === 'mean_risk') setSortAsc(!sortAsc);
                else {
                  setSortField('mean_risk');
                  setSortAsc(false);
                }
              }}
              className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded ${
                sortField === 'mean_risk' ? 'bg-white/10 text-emerald-400' : 'hover:text-white'
              }`}
            >
              Risk <ArrowUpDown className="w-2.5 h-2.5" />
            </button>
            <button
              onClick={() => {
                if (sortField === 'area_acres') setSortAsc(!sortAsc);
                else {
                  setSortField('area_acres');
                  setSortAsc(false);
                }
              }}
              className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded ${
                sortField === 'area_acres' ? 'bg-white/10 text-emerald-400' : 'hover:text-white'
              }`}
            >
              Area <ArrowUpDown className="w-2.5 h-2.5" />
            </button>
          </div>
        </div>

        {sortedZones.length === 0 ? (
          <p className="text-xs text-slate-500 py-3 text-center">No zones above current threshold.</p>
        ) : (
          <div className="overflow-x-auto max-h-48 overflow-y-auto space-y-1.5 pr-1">
            {sortedZones.map(({ properties, coordinates }) => {
              const isSelected = selectedZoneId === properties.zone_id;
              return (
                <div
                  key={properties.zone_id}
                  onClick={() => onSelectZone(properties.zone_id, coordinates)}
                  className={`p-2.5 rounded-lg border text-xs cursor-pointer flex items-center justify-between transition-all ${
                    isSelected
                      ? 'bg-red-500/15 border-red-500/50 text-white shadow'
                      : 'bg-slate-900/50 border-white/5 hover:bg-slate-800/40 text-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-400" />
                    <div>
                      <span className="font-semibold text-white">Zone #{properties.zone_id}</span>
                      <span className="text-[10px] text-slate-400 block font-mono">
                        {properties.top_anomaly}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 text-right font-mono text-[11px]">
                    <div>
                      <span className="text-emerald-400 font-bold">
                        {(properties.mean_risk * 100).toFixed(0)}%
                      </span>
                      <span className="text-[10px] text-slate-500 block">mean risk</span>
                    </div>
                    <div>
                      <span className="text-white font-medium">{properties.area_acres} ac</span>
                      <span className="text-[10px] text-slate-500 block">area</span>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

