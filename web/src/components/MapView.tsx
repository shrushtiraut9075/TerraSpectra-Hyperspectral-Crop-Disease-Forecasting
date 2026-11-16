import React, { useMemo, useState } from 'react';
import DeckGL from '@deck.gl/react';
import { MapView as DeckMapView } from '@deck.gl/core';
import { GeoJsonLayer, ScatterplotLayer, BitmapLayer } from '@deck.gl/layers';
import { TileLayer } from '@deck.gl/geo-layers';
import { Map } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

import { Scene, GroundControlPoint } from '../types';
import { useUIStore } from '../store/uiStore';
import { Compass, Maximize2, RotateCcw, Globe, Map as MapIcon } from 'lucide-react';

interface MapViewProps {
  scene: Scene | null;
  zonesGeoJson: any | null;
  gcps?: GroundControlPoint[];
  onSelectZone: (zoneId: number) => void;
}

export const MapView: React.FC<MapViewProps> = ({
  scene,
  zonesGeoJson,
  gcps = [],
  onSelectZone,
}) => {
  const {
    layers,
    opacity,
    selectedZoneId,
    threshold,
    colorRamp,
    basemap,
    setBasemap,
    targetLocation,
    setTargetLocation,
  } = useUIStore();
  const [hoverInfo, setHoverInfo] = useState<any>(null);

  // Compute center lat/lon from scene bounds [min_lon, min_lat, max_lon, max_lat]
  const initialViewState = useMemo(() => {
    if (scene && scene.bounds_wgs84) {
      const [minLon, minLat, maxLon, maxLat] = scene.bounds_wgs84;
      return {
        longitude: (minLon + maxLon) / 2,
        latitude: (minLat + maxLat) / 2,
        zoom: 14.5,
        pitch: layers.terrain ? 50 : 0,
        bearing: -15,
        maxPitch: 85,
      };
    }
    // Default near Pune agricultural belt
    return {
      longitude: 73.7023,
      latitude: 18.491,
      zoom: 14.5,
      pitch: 50,
      bearing: -15,
      maxPitch: 85,
    };
  }, [scene, layers.terrain]);

  const [viewState, setViewState] = useState(initialViewState);

  // Synchronize viewState when scene changes
  React.useEffect(() => {
    setViewState(initialViewState);
  }, [initialViewState]);

  // Smoothly fly to searched village or custom location
  React.useEffect(() => {
    if (targetLocation) {
      setViewState((prev) => ({
        ...prev,
        longitude: targetLocation[0],
        latitude: targetLocation[1],
        zoom: 15.2,
        pitch: 45,
        bearing: -15,
      }));
      setTargetLocation(null);
    }
  }, [targetLocation, setTargetLocation]);

  // Construct Deck.gl Layers
  const deckLayers = useMemo(() => {
    const list: any[] = [];
    if (!scene) return list;

    // 1. High-visibility Farm boundary polygon + corner GPS pins
    if (layers.farmBoundary && scene.bounds_wgs84) {
      const [minLon, minLat, maxLon, maxLat] = scene.bounds_wgs84;
      const boundaryFeature = {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [minLon, minLat],
              [maxLon, minLat],
              [maxLon, maxLat],
              [minLon, maxLat],
              [minLon, minLat],
            ],
          ],
        },
      };

      // Vibrant glowing emerald boundary
      list.push(
        new GeoJsonLayer({
          id: `farm-boundary-layer-${scene.id}`,
          data: boundaryFeature as any,
          stroked: true,
          filled: true,
          lineWidthMinPixels: 3.5,
          lineWidthMaxPixels: 8,
          getLineColor: [16, 230, 140, 255], // Ultra-vibrant Emerald border
          getFillColor: [16, 185, 129, 32],  // Translucent green tint
          pickable: false,
        })
      );

      // 4 GPS surveyor corner pins
      const corners = [
        { lon: minLon, lat: minLat, id: 'SW' },
        { lon: maxLon, lat: minLat, id: 'SE' },
        { lon: maxLon, lat: maxLat, id: 'NE' },
        { lon: minLon, lat: maxLat, id: 'NW' },
      ];

      list.push(
        new ScatterplotLayer({
          id: `farm-corners-${scene.id}`,
          data: corners,
          pickable: false,
          opacity: 1,
          stroked: true,
          filled: true,
          radiusMinPixels: 5,
          radiusMaxPixels: 9,
          lineWidthMinPixels: 2,
          getPosition: (d: any) => [d.lon, d.lat],
          getFillColor: [16, 230, 140, 255],
          getLineColor: [255, 255, 255, 255],
        })
      );
    }

    // 2. Risk Heatmap TileLayer (served from FastAPI XYZ PNG tile endpoint)
    if (layers.risk) {
      const tileUrl = `/api/v1/scenes/${scene.id}/tiles/{z}/{x}/{y}.png?threshold=${threshold}&cmap=${colorRamp}`;
      list.push(
        new TileLayer({
          id: `risk-tiles-${scene.id}-${threshold}-${colorRamp}`,
          data: tileUrl,
          minZoom: 10,
          maxZoom: 19,
          tileSize: 256,
          opacity: opacity,
          renderSubLayers: (props: any) => {
            const {
              bbox: { west, south, east, north },
            } = props.tile;

            return new (BitmapLayer as any)(props, {
              image: props.data,
              bounds: [west, south, east, north],
            });
          },
        })
      );
    }

    // 3. Risk Zones GeoJSON Layer (Polygons exceeding threshold)
    if (layers.zones && zonesGeoJson) {
      list.push(
        new GeoJsonLayer({
          id: `zones-layer-${scene.id}-${threshold}`,
          data: zonesGeoJson,
          pickable: true,
          stroked: true,
          filled: true,
          lineWidthMinPixels: 2.5,
          getFillColor: (f: any) => {
            const isSelected = f.properties?.zone_id === selectedZoneId;
            return isSelected ? [239, 68, 68, 140] : [239, 68, 68, 60];
          },
          getLineColor: (f: any) => {
            const isSelected = f.properties?.zone_id === selectedZoneId;
            return isSelected ? [255, 255, 255, 255] : [239, 68, 68, 220];
          },
          onHover: (info: any) => setHoverInfo(info),
          onClick: (info: any) => {
            if (info.object?.properties?.zone_id) {
              onSelectZone(info.object.properties.zone_id);
            }
          },
        })
      );
    }

    // 4. Ground Control Points (GCP) Debug Layer
    if (layers.gcps && gcps.length > 0) {
      list.push(
        new ScatterplotLayer({
          id: 'gcp-markers-layer',
          data: gcps,
          pickable: true,
          opacity: 0.9,
          stroked: true,
          filled: true,
          radiusScale: 1,
          radiusMinPixels: 6,
          radiusMaxPixels: 14,
          lineWidthMinPixels: 2,
          getPosition: (d: GroundControlPoint) => [d.lon, d.lat],
          getFillColor: [56, 189, 248, 200], // Sky blue marker
          getLineColor: [255, 255, 255, 255],
          onHover: (info: any) => {
            if (info.object) {
              setHoverInfo({
                ...info,
                isGcp: true,
              });
            } else {
              setHoverInfo(null);
            }
          },
        })
      );
    }

    return list;
  }, [scene, layers, zonesGeoJson, gcps, opacity, threshold, colorRamp, selectedZoneId, onSelectZone]);

  return (
    <div className="relative w-full h-full bg-[#0b0f17] overflow-hidden">
      {/* 1. MapLibre Base Map Layer (Background z-0) */}
      <div className="absolute inset-0 w-full h-full z-0 pointer-events-none">
        <MapLibreMap viewState={viewState} basemap={basemap} />
      </div>

      {/* 2. DeckGL Interactive Canvas Layer (Foreground z-10) */}
      <div className="absolute inset-0 w-full h-full z-10">
        <DeckGL
          viewState={viewState}
          onViewStateChange={({ viewState: newVs }) => setViewState(newVs as any)}
          controller={{ doubleClickZoom: true, touchRotate: true }}
          layers={deckLayers}
          views={new DeckMapView({ repeat: true })}
          getCursor={({ isHovering }) => (isHovering ? 'pointer' : 'default')}
          style={{ width: '100%', height: '100%' }}
        />
      </div>

      {/* Floating Camera Quick Controls */}
      <div className="absolute top-4 right-4 z-20 flex flex-col gap-1.5 glass-panel p-1.5 rounded-xl border border-white/10 shadow-xl">
        <button
          onClick={() => {
            const next = basemap === 'satellite' ? 'dark' : basemap === 'dark' ? 'streets' : 'satellite';
            setBasemap(next);
          }}
          className="p-2 rounded-lg hover:bg-white/10 text-slate-300 hover:text-white transition-colors"
          title={`Switch basemap (current: ${basemap})`}
        >
          {basemap === 'satellite' ? (
            <Globe className="w-4 h-4 text-emerald-400" />
          ) : (
            <MapIcon className="w-4 h-4 text-sky-400" />
          )}
        </button>
        <button
          onClick={() => setViewState({ ...viewState, pitch: viewState.pitch > 10 ? 0 : 55 })}
          className="p-2 rounded-lg hover:bg-white/10 text-slate-300 hover:text-white transition-colors"
          title="Toggle 2D / 3D Pitch"
        >
          <Compass className="w-4 h-4" />
        </button>
        <button
          onClick={() => setViewState(initialViewState)}
          className="p-2 rounded-lg hover:bg-white/10 text-slate-300 hover:text-white transition-colors"
          title="Reset Camera View"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Interactive Tooltip */}
      {hoverInfo && hoverInfo.object && (
        <div
          className="absolute z-30 glass-panel p-2.5 rounded-xl border border-white/15 text-xs shadow-2xl pointer-events-none transform -translate-x-1/2 -translate-y-full mb-3"
          style={{ left: hoverInfo.x, top: hoverInfo.y }}
        >
          {hoverInfo.isGcp ? (
            <div className="space-y-1 font-mono">
              <div className="text-sky-400 font-bold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-sky-400" />
                Ground Control Point
              </div>
              <p className="text-slate-300">
                Raster Pixel: ({hoverInfo.object.col}, {hoverInfo.object.row})
              </p>
              <p className="text-slate-400 text-[10px]">
                GPS: {hoverInfo.object.lat.toFixed(6)}°N, {hoverInfo.object.lon.toFixed(6)}°E
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              <div className="text-red-400 font-bold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-red-400 animate-ping" />
                Risk Zone #{hoverInfo.object.properties?.zone_id}
              </div>
              <div className="text-[11px] text-slate-300 font-mono space-y-0.5">
                <p>
                  Area:{' '}
                  <span className="font-semibold text-white">
                    {hoverInfo.object.properties?.area_acres} acres
                  </span>
                </p>
                <p>
                  Mean Risk:{' '}
                  <span className="font-bold text-emerald-400">
                    {(hoverInfo.object.properties?.mean_risk * 100).toFixed(0)}%
                  </span>{' '}
                  (Max: {(hoverInfo.object.properties?.max_risk * 100).toFixed(0)}%)
                </p>
                <p className="text-slate-400 text-[10px]">
                  Dominant Anomaly: {hoverInfo.object.properties?.top_anomaly}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const BASEMAP_CONFIGS = {
  satellite: {
    tiles: [
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    ],
    attribution: '&copy; Esri, Maxar, Earthstar Geographics',
    maxzoom: 19,
  },
  dark: {
    tiles: [
      'https://services.arcgisonline.com/arcgis/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    ],
    attribution: '&copy; Esri, HERE, Garmin',
    maxzoom: 16,
  },
  streets: {
    tiles: [
      'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    ],
    attribution: '&copy; OpenStreetMap contributors',
    maxzoom: 19,
  },
};

// MapLibre background canvas
const MapLibreMap: React.FC<{ viewState: any; basemap: 'satellite' | 'dark' | 'streets' }> = ({
  viewState,
  basemap,
}) => {
  const mapContainerRef = React.useRef<HTMLDivElement>(null);
  const mapRef = React.useRef<Map | null>(null);

  const createStyle = (mode: 'satellite' | 'dark' | 'streets') => {
    const cfg = BASEMAP_CONFIGS[mode] || BASEMAP_CONFIGS.satellite;
    return {
      version: 8 as const,
      sources: {
        'basemap-source': {
          type: 'raster' as const,
          tiles: cfg.tiles,
          tileSize: 256,
          attribution: cfg.attribution,
        },
      },
      layers: [
        {
          id: 'basemap-layer',
          type: 'raster' as const,
          source: 'basemap-source',
          minzoom: 0,
          maxzoom: cfg.maxzoom,
        },
      ],
    };
  };

  React.useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new Map({
      container: mapContainerRef.current,
      style: createStyle(basemap),
      center: [viewState.longitude, viewState.latitude],
      zoom: viewState.zoom,
      pitch: viewState.pitch,
      bearing: viewState.bearing,
      interactive: false,
    });

    mapRef.current = map;
    return () => map.remove();
  }, []);

  // Update style when basemap changes
  React.useEffect(() => {
    if (mapRef.current) {
      mapRef.current.setStyle(createStyle(basemap));
    }
  }, [basemap]);

  // Synchronize camera
  React.useEffect(() => {
    if (mapRef.current) {
      mapRef.current.jumpTo({
        center: [viewState.longitude, viewState.latitude],
        zoom: viewState.zoom,
        pitch: viewState.pitch,
        bearing: viewState.bearing,
      });
    }
  }, [viewState]);

  return <div ref={mapContainerRef} className="w-full h-full pointer-events-none" />;
};
