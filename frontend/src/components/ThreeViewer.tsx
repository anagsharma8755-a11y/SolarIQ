import { useRef, useMemo, useEffect, useState, useCallback } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Text, Html } from "@react-three/drei";
import * as THREE from "three";
import type {
  DemoBuilding,
  BuildingAnalysisResponse,
  CityAnalysisResponse,
  CameraState,
  AnalyzedSurface,
} from "../lib/types";

// ─── Surface color utilities ───

function suitabilityColor(score: number, heatmapMode: boolean): string {
  if (!heatmapMode) {
    return "#FFB300"; // default solar amber
  }
  if (score >= 0.8) return "#4CAF50"; // excellent - green
  if (score >= 0.6) return "#66BB6A"; // high - light green
  if (score >= 0.4) return "#FFC107"; // moderate - amber
  if (score >= 0.2) return "#FF9800"; // low - orange
  return "#F44336"; // poor - red
}

function surfaceTypeColor(type: string): string {
  switch (type) {
    case "roof": return "#FFB300";
    case "facade": return "#42A5F5";
    case "ground": return "#78909C";
    default: return "#9E9E9E";
  }
}

// ─── Building mesh component ───

function BuildingMesh({
  demo,
  analysisData,
  heatmapMode,
  selectedSurfaceId,
  position,
  onSelectBuilding,
  onSelectSurface,
}: {
  demo: DemoBuilding;
  analysisData: BuildingAnalysisResponse | null;
  heatmapMode: boolean;
  selectedSurfaceId: string | null;
  position: [number, number, number];
  onSelectBuilding: (b: DemoBuilding) => void;
  onSelectSurface: (s: AnalyzedSurface) => void;
}) {
  const meshRef = useRef<THREE.Group>(null);
  const [hoveredSurface, setHoveredSurface] = useState<string | null>(null);
  const [hovered, setHovered] = useState(false);

  // Create geometries from vertices
  const surfaces = useMemo(() => {
    if (analysisData) {
      return analysisData.surfaces;
    }
    // Fallback: create from demo vertices without analysis
    return demo.surfaces.map((s) => ({
      surface_id: s.surface_id || "unknown",
      building_id: demo.building_id,
      area_m2: 0,
      normal: { x: 0, y: 0, z: 1 },
      azimuth_deg: 0,
      tilt_deg: 0,
      surface_type: "roof",
      vertices: s.vertices,
      solar_score: 0.5,
      solar_suitability: "moderate",
      energy_potential: { usable_area_m2: 0, estimated_capacity_kw: 0, estimated_annual_energy_kwh: 0 },
      ml_prediction: null,
    }));
  }, [analysisData, demo]);

  const handleSurfaceClick = useCallback(
    (e: any, surface: AnalyzedSurface) => {
      e.stopPropagation?.();
      onSelectSurface(surface);
    },
    [onSelectSurface]
  );

  const handleBuildingClick = useCallback(
    (e: any) => {
      e.stopPropagation?.();
      onSelectBuilding(demo);
    },
    [demo, onSelectBuilding]
  );

  return (
    <group ref={meshRef} position={position}>
      {surfaces.map((surface) => {
        const verts = surface.vertices;
        if (!verts || verts.length < 3) return null;

        const isSelected = selectedSurfaceId === surface.surface_id;
        const isHovered = hoveredSurface === surface.surface_id;

        // Build BufferGeometry from vertices
        const geometry = useMemo(() => {
          const geo = new THREE.BufferGeometry();
          // Triangulate the polygon (fan from first vertex)
          const positions: number[] = [];
          for (let i = 1; i < verts.length - 1; i++) {
            positions.push(...verts[0], ...verts[i], ...verts[i + 1]);
          }
          geo.setAttribute(
            "position",
            new THREE.Float32BufferAttribute(positions, 3)
          );
          geo.computeVertexNormals();
          return geo;
        }, [verts]);

        const color = useMemo(
          () => suitabilityColor(surface.solar_score, heatmapMode),
          [surface.solar_score, heatmapMode]
        );

        return (
          <mesh
            key={surface.surface_id}
            geometry={geometry}
            onClick={(e) => handleSurfaceClick(e, surface)}
            onPointerEnter={(e: any) => {
              e.stopPropagation?.();
              setHoveredSurface(surface.surface_id);
              document.body.style.cursor = "pointer";
            }}
            onPointerLeave={() => {
              setHoveredSurface(null);
              document.body.style.cursor = "default";
            }}
          >
            <meshStandardMaterial
              color={color}
              transparent
              opacity={isSelected ? 0.95 : isHovered ? 0.85 : 0.7}
              side={THREE.DoubleSide}
              emissive={isSelected ? color : isHovered ? color : "#000000"}
              emissiveIntensity={isSelected ? 0.3 : isHovered ? 0.15 : 0}
              wireframe={false}
              depthWrite={!isHovered}
            />
            {isHovered && (
              <Html distanceFactor={15} position={[0, 0, 0]} center>
                <div className="glass-panel px-2 py-1 text-[10px] text-white whitespace-nowrap pointer-events-none">
                  <div className="font-medium">{surface.surface_id}</div>
                  <div className="text-dark-300">
                    {(surface.solar_score * 100).toFixed(0)}% · {surface.surface_type}
                  </div>
                </div>
              </Html>
            )}
          </mesh>
        );
      })}

      {/* Wireframe overlay */}
      <group>
        {surfaces.map((surface) => {
          const verts = surface.vertices;
          if (!verts || verts.length < 3) return null;
          const edges: number[] = [];
          for (let i = 0; i < verts.length; i++) {
            const a = verts[i];
            const b = verts[(i + 1) % verts.length];
            edges.push(a[0], a[1], a[2], b[0], b[1], b[2]);
          }
          const geo = new THREE.BufferGeometry();
          geo.setAttribute(
            "position",
            new THREE.Float32BufferAttribute(edges, 3)
          );
          return (
            <lineSegments
              key={`wire-${surface.surface_id}`}
              geometry={geo}
            >
              <lineBasicMaterial
                color={hoveredSurface === surface.surface_id ? "#ffffff" : "#ffffff20"}
                transparent
                opacity={hoveredSurface === surface.surface_id ? 0.8 : 0.15}
              />
            </lineSegments>
          );
        })}
      </group>

      {/* Building label */}
      <Text
        position={[
          (surfaces[0]?.vertices[0]?.[0] ?? 0) + (surfaces[0]?.vertices[1]?.[0] ?? 10) / 2,
          -1.5,
          (surfaces[0]?.vertices[0]?.[2] ?? 0) + (surfaces[0]?.vertices[2]?.[2] ?? 10) / 2,
        ]}
        fontSize={1.2}
        color="#ffffff40"
        anchorX="center"
        anchorY="middle"
      >
        {demo.building_id}
      </Text>
    </group>
  );
}

// ─── Ground plane ───

function Ground() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[45, -0.01, 25]}>
      <planeGeometry args={[150, 120]} />
      <meshStandardMaterial
        color="#0E0F11"
        transparent
        opacity={0.8}
      />
    </mesh>
  );
}

// ─── Grid ───

function GridLines() {
  return (
    <gridHelper
      args={[150, 60, "#1E1F22", "#1E1F22"]}
      position={[45, 0, 25]}
    />
  );
}

// ─── Camera controller ───

function CameraController({
  cameraState,
  analysisData,
}: {
  cameraState: CameraState;
  analysisData: BuildingAnalysisResponse | null;
}) {
  const { camera } = useThree();
  const targetPos = useRef(new THREE.Vector3(45, 40, 55));
  const targetLookAt = useRef(new THREE.Vector3(45, 5, 25));

  useEffect(() => {
    switch (cameraState) {
      case "city":
        targetPos.current.set(45, 40, 55);
        targetLookAt.current.set(45, 5, 25);
        break;
      case "building":
        if (analysisData) {
          const s = analysisData.surfaces[0]?.vertices;
          if (s) {
            const cx = s.reduce((sum, v) => sum + v[0], 0) / s.length;
            const cz = s.reduce((sum, v) => sum + v[2], 0) / s.length;
            targetPos.current.set(cx + 15, 15, cz + 15);
            targetLookAt.current.set(cx, 5, cz);
          }
        }
        break;
      case "surface":
        if (analysisData) {
          const s = analysisData.surfaces[0]?.vertices;
          if (s) {
            const cx = s.reduce((sum, v) => sum + v[0], 0) / s.length;
            const cz = s.reduce((sum, v) => sum + v[2], 0) / s.length;
            targetPos.current.set(cx + 8, 12, cz + 8);
            targetLookAt.current.set(cx, 8, cz);
          }
        }
        break;
      case "analysis":
        targetPos.current.set(45, 45, 45);
        targetLookAt.current.set(45, 5, 25);
        break;
      case "overview":
        targetPos.current.set(45, 60, 60);
        targetLookAt.current.set(45, 0, 25);
        break;
    }
  }, [cameraState, analysisData]);

  useFrame(() => {
    const d = 0.03;
    camera.position.lerp(targetPos.current, d);
    const currentLookAt = new THREE.Vector3();
    camera.getWorldDirection(currentLookAt);
    currentLookAt.multiplyScalar(30).add(camera.position);
    currentLookAt.lerp(targetLookAt.current, d);
  });

  return null;
}

// ─── Main viewer ───

export default function ThreeViewer({
  buildings,
  analysisData,
  cityData,
  cameraState,
  heatmapMode,
  selectedSurfaceId,
  onSelectBuilding,
  onSelectSurface,
}: {
  buildings: DemoBuilding[];
  analysisData: BuildingAnalysisResponse | null;
  cityData: CityAnalysisResponse | null;
  cameraState: CameraState;
  heatmapMode: boolean;
  selectedSurfaceId: string | null;
  onSelectBuilding: (b: DemoBuilding) => void;
  onSelectSurface: (s: AnalyzedSurface) => void;
}) {
  const reducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  return (
    <div className="h-full w-full bg-dark-950">
      <Canvas
        camera={{ position: [45, 40, 55], fov: 45, near: 0.1, far: 500 }}
        gl={{
          antialias: true,
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.2,
        }}
        dpr={[1, 2]}
      >
        <color attach="background" args={["#0a0b0d"]} />

        {/* Lighting */}
        <ambientLight intensity={0.4} />
        <directionalLight
          position={[30, 40, 20]}
          intensity={1.2}
          color="#FFF8E1"
          castShadow
        />
        <directionalLight
          position={[-20, 10, -10]}
          intensity={0.3}
          color="#42A5F5"
        />

        {/* Ground */}
        <Ground />
        <GridLines />

        {/* Buildings */}
        {buildings.map((demo) => {
          const analysis = cityData?.buildings.find(
            (b) => b.building_id === demo.building_id
          );
          return (
            <BuildingMesh
              key={demo.building_id}
              demo={demo}
              analysisData={
                analysisData?.building_id === demo.building_id
                  ? analysisData
                  : analysis ?? null
              }
              heatmapMode={heatmapMode}
              selectedSurfaceId={
                analysisData?.building_id === demo.building_id
                  ? selectedSurfaceId
                  : null
              }
              position={[0, 0, 0]}
              onSelectBuilding={onSelectBuilding}
              onSelectSurface={onSelectSurface}
            />
          );
        })}

        {/* Camera */}
        <CameraController
          cameraState={cameraState}
          analysisData={analysisData}
        />

        <OrbitControls
          enableDamping
          dampingFactor={reducedMotion ? 0.1 : 0.05}
          enablePan
          enableZoom
          maxPolarAngle={Math.PI / 2.1}
          minDistance={5}
          maxDistance={100}
        />
      </Canvas>
    </div>
  );
}
