import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { AreaAnalysisResponse, GISBuilding } from "../lib/types";
import { fadeIn, slideInUp } from "../lib/animations";

interface MapViewProps {
  center: [number, number];
  radiusMeters: number;
  areaData: AreaAnalysisResponse | null;
  selectedBuilding: GISBuilding | null;
  onSelectBuilding: (building: GISBuilding) => void;
}

export function MapView({
  center,
  radiusMeters,
  areaData,
  selectedBuilding,
  onSelectBuilding,
}: MapViewProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const geojsonLayerRef = useRef<L.GeoJSON | null>(null);
  const circleLayerRef = useRef<L.Circle | null>(null);
  const markerLayerRef = useRef<L.Marker | null>(null);
  const legendRef = useRef<HTMLDivElement>(null);

  // Initialize Leaflet Map once
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center,
      zoom: 16,
      zoomControl: false,
    });

    // Add zoom control at top-right
    L.control.zoom({ position: "topright" }).addTo(map);

    // OpenStreetMap dark-friendly base tiles
    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
      {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: "abcd",
        maxZoom: 20,
      }
    ).addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Animate legend entrance
  useEffect(() => {
    if (!legendRef.current) return;
    const cleanup = slideInUp(legendRef.current, { duration: 500, delay: 300 });
    return cleanup;
  }, []);

  // Update center, radius circle, and center marker
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    map.flyTo(center, 16, { duration: 1.2 });

    // Update center marker
    if (markerLayerRef.current) {
      markerLayerRef.current.remove();
    }
    const centerIcon = L.divIcon({
      className: "custom-center-marker",
      html: `
        <div class="relative flex items-center justify-center">
          <div class="w-4 h-4 bg-solar-500 rounded-full border-2 border-white shadow-lg animate-pulse"></div>
          <div class="absolute w-8 h-8 bg-solar-500/20 rounded-full animate-ping pointer-events-none"></div>
        </div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });
    markerLayerRef.current = L.marker(center, { icon: centerIcon }).addTo(map);

    // Update radius circle
    if (circleLayerRef.current) {
      circleLayerRef.current.remove();
    }
    circleLayerRef.current = L.circle(center, {
      radius: radiusMeters,
      color: "#f59e0b",
      weight: 1.5,
      opacity: 0.8,
      fillColor: "#f59e0b",
      fillOpacity: 0.06,
      dashArray: "6, 8",
    }).addTo(map);
  }, [center, radiusMeters]);

  // Render building polygons with solar suitability styling
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !areaData) return;

    if (geojsonLayerRef.current) {
      geojsonLayerRef.current.remove();
    }

    const geojson = areaData.geojson;
    if (!geojson || !geojson.features) return;

    const layer = L.geoJSON(geojson as any, {
      style: (feature) => {
        const props = feature?.properties || {};
        const isSelected = selectedBuilding?.building_id === props.building_id;
        const color = props.color || "#10b981";

        return {
          fillColor: color,
          fillOpacity: isSelected ? 0.9 : 0.65,
          color: isSelected ? "#ffffff" : color,
          weight: isSelected ? 3 : 1.5,
        };
      },
      onEachFeature: (feature, featureLayer) => {
        const props = feature.properties || {};
        const building = areaData.buildings.find(
          (b) => b.building_id === props.building_id
        );

        // Tooltip on hover
        featureLayer.bindTooltip(
          `
          <div class="p-1 font-sans">
            <div class="font-bold text-white text-xs">${props.name || props.building_id}</div>
            <div class="text-[11px] text-amber-300">Score: ${props.solar_score} · ${props.solar_suitability?.toUpperCase()}</div>
            <div class="text-[10px] text-gray-300">${props.estimated_capacity_kw} kW · ${props.usable_area_m2} m²</div>
          </div>
          `,
          {
            sticky: true,
            className: "leaflet-dark-tooltip",
          }
        );

        // Click handler to select building
        featureLayer.on("click", () => {
          if (building) {
            onSelectBuilding(building);
          }
        });
      },
    }).addTo(map);

    geojsonLayerRef.current = layer;
  }, [areaData, selectedBuilding, onSelectBuilding]);

  return (
    <div className="relative w-full h-full bg-dark-950">
      <div ref={mapContainerRef} className="w-full h-full z-0" />

      {/* Map Legend Overlay */}
      <div
        ref={legendRef}
        className="absolute top-4 left-4 z-10 glass-panel-solid p-3 rounded-lg text-xs space-y-1.5 shadow-xl backdrop-blur-md opacity-0"
      >
        <div className="font-semibold text-white mb-1">Solar Potential Legend</div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm bg-emerald-500"></div>
          <span className="text-dark-200">High (Score &ge; 0.70)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm bg-amber-500"></div>
          <span className="text-dark-200">Medium (0.45 &ndash; 0.70)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm bg-slate-500"></div>
          <span className="text-dark-200">Low (&lt; 0.45)</span>
        </div>
        {areaData?.data_provenance && (
          <div className="pt-1.5 mt-1.5 border-t border-white/10 text-[10px]">
            <span
              className={`px-1.5 py-0.5 rounded font-mono font-medium ${
                areaData.data_provenance.is_live_data
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                  : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
              }`}
            >
              {areaData.data_provenance.source}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
