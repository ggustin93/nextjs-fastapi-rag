'use client';

import { useEffect, useMemo, useRef } from 'react';
import { MapPin, X, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

// Types for OSIRIS worksite geometry
export interface WorksiteGeometry {
  type: 'MultiPolygon' | 'Polygon';
  coordinates: number[][][][] | number[][][];
}

export interface WorksiteInfo {
  id_ws: string;
  label_fr?: string;
  label_nl?: string;
  status_fr?: string;
  status_nl?: string;
  road_impl_fr?: string;
  road_impl_nl?: string;
  pgm_start_date?: string;
  pgm_end_date?: string;
}

interface WorksiteMapViewerProps {
  geometry: WorksiteGeometry;
  worksiteInfo?: WorksiteInfo;
  language?: 'fr' | 'nl';
  onClose?: () => void;
}

// Dynamically import Leaflet components (SSR-safe)
function LeafletMap({
  geometry,
  worksiteInfo,
  language = 'fr'
}: Omit<WorksiteMapViewerProps, 'onClose'>) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  // Calculate bounds from geometry
  const bounds = useMemo(() => {
    const coords: [number, number][] = [];

    const extractCoords = (arr: unknown[]): void => {
      // Check if this is a ring (array of coordinate pairs like [[lng, lat], [lng, lat], ...])
      if (Array.isArray(arr[0]) && arr[0].length === 2 && typeof arr[0][0] === 'number' && typeof arr[0][1] === 'number') {
        // This is a ring of coordinate pairs - iterate through each point
        arr.forEach(coord => {
          const pair = coord as [number, number];
          coords.push([pair[1], pair[0]]); // Leaflet uses [lat, lng], GeoJSON uses [lng, lat]
        });
      } else if (Array.isArray(arr[0])) {
        // This is a nested structure (MultiPolygon or Polygon outer array) - recurse
        arr.forEach(item => extractCoords(item as unknown[]));
      }
    };

    extractCoords(geometry.coordinates as unknown[]);
    return coords;
  }, [geometry]);

  useEffect(() => {
    // Only run on client
    if (typeof window === 'undefined' || !mapRef.current) return;

    let map: L.Map | null = null;

    const initMap = async () => {
      // Dynamic import of Leaflet
      const L = await import('leaflet');
      // @ts-ignore - CSS import
      await import('leaflet/dist/leaflet.css');

      // Fix Leaflet marker icons
      delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      });

      if (!mapRef.current || mapInstanceRef.current) return;

      // Create map centered on Brussels
      map = L.map(mapRef.current).setView([50.8503, 4.3517], 13);
      mapInstanceRef.current = map;

      // Add OpenStreetMap tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(map);

      // Convert OSIRIS coordinates to Leaflet format (swap lng/lat to lat/lng)
      const convertCoords = (coords: number[][][]): L.LatLngExpression[][] => {
        return coords.map(ring =>
          ring.map(point => [point[1], point[0]] as L.LatLngExpression)
        );
      };

      // Add polygon(s)
      const polygonStyle = {
        color: '#ff7800',
        weight: 3,
        opacity: 0.8,
        fillColor: '#ff7800',
        fillOpacity: 0.35,
      };

      let polygonLayer: L.Polygon | L.LayerGroup;

      if (geometry.type === 'MultiPolygon') {
        const multiCoords = geometry.coordinates as number[][][][];
        const layers = multiCoords.map(poly =>
          L.polygon(convertCoords(poly), polygonStyle)
        );
        polygonLayer = L.layerGroup(layers).addTo(map);

        // Fit bounds to all polygons
        const allBounds = layers.reduce((acc, layer) =>
          acc.extend(layer.getBounds()),
          L.latLngBounds([])
        );
        map.fitBounds(allBounds, { padding: [50, 50] });
      } else {
        const singleCoords = geometry.coordinates as number[][][];
        polygonLayer = L.polygon(convertCoords(singleCoords), polygonStyle).addTo(map);
        map.fitBounds(polygonLayer.getBounds(), { padding: [50, 50] });
      }

      // Add popup with worksite info
      if (worksiteInfo && bounds.length > 0) {
        const label = language === 'fr' ? worksiteInfo.label_fr : worksiteInfo.label_nl;
        const status = language === 'fr' ? worksiteInfo.status_fr : worksiteInfo.status_nl;
        const roads = language === 'fr' ? worksiteInfo.road_impl_fr : worksiteInfo.road_impl_nl;

        const popupContent = `
          <div class="text-sm">
            <strong>${label || `Worksite ${worksiteInfo.id_ws}`}</strong>
            ${status ? `<br/><span class="text-muted-foreground">Status: ${status}</span>` : ''}
            ${roads ? `<br/><span class="text-muted-foreground">Roads: ${roads}</span>` : ''}
          </div>
        `;

        // Calculate centroid for popup
        const centroid = bounds.reduce(
          (acc, coord) => [acc[0] + coord[0] / bounds.length, acc[1] + coord[1] / bounds.length],
          [0, 0]
        );

        L.marker(centroid as L.LatLngExpression)
          .addTo(map)
          .bindPopup(popupContent)
          .openPopup();
      }
    };

    initMap();

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [geometry, worksiteInfo, language, bounds]);

  return (
    <div
      ref={mapRef}
      className="w-full h-full min-h-[300px]"
      style={{ zIndex: 0 }}
    />
  );
}

export function WorksiteMapViewer({
  geometry,
  worksiteInfo,
  language = 'fr',
  onClose
}: WorksiteMapViewerProps) {
  const label = language === 'fr' ? worksiteInfo?.label_fr : worksiteInfo?.label_nl;
  const status = language === 'fr' ? worksiteInfo?.status_fr : worksiteInfo?.status_nl;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b bg-muted/30 p-3">
        <div className="flex items-center gap-2">
          <MapPin className="h-4 w-4 text-orange-500" />
          <span className="font-medium text-sm truncate max-w-[200px]">
            {label || `Worksite ${worksiteInfo?.id_ws || ''}`}
          </span>
          {status && (
            <Badge variant="outline" className="text-xs">
              {status}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-1">
          {worksiteInfo?.id_ws && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 gap-1"
              onClick={() => window.open('https://osiris.brussels', '_blank')}
            >
              <ExternalLink className="h-3 w-3" />
              <span className="text-xs">OSIRIS</span>
            </Button>
          )}
          {onClose && (
            <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Map Container */}
      <div className="flex-1 relative">
        <LeafletMap
          geometry={geometry}
          worksiteInfo={worksiteInfo}
          language={language}
        />
      </div>

      {/* Footer with info */}
      {worksiteInfo && (
        <div className="border-t bg-muted/30 p-2 text-xs text-muted-foreground">
          <div className="flex items-center justify-between">
            <span>
              {worksiteInfo.pgm_start_date && worksiteInfo.pgm_end_date && (
                <>
                  {new Date(worksiteInfo.pgm_start_date).toLocaleDateString(language)}
                  {' → '}
                  {new Date(worksiteInfo.pgm_end_date).toLocaleDateString(language)}
                </>
              )}
            </span>
            <span className="text-orange-500 font-mono">
              ID: {worksiteInfo.id_ws}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
