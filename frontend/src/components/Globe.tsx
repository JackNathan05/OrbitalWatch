"use client";

import { useEffect, useRef, useState } from "react";
import type { SatellitePosition } from "@/lib/types";
import { OBJECT_TYPE_COLORS } from "@/lib/types";

// Cesium is loaded from CDN at runtime. The `window.Cesium` global
// avoids Turbopack's strict-mode parsing of Cesium's internal chunks,
// which contain octal escape sequences that ESM strict mode rejects.
declare global {
  interface Window {
    Cesium: typeof import("cesium");
    CESIUM_BASE_URL: string;
  }
}

const CESIUM_VERSION = "1.140";
const CESIUM_CDN = `https://cdn.jsdelivr.net/npm/cesium@${CESIUM_VERSION}/Build/Cesium`;

interface GlobeProps {
  positions: SatellitePosition[];
  onSatelliteClick?: (satellite: SatellitePosition) => void;
  onConjunctionFocus?: { lat: number; lon: number; alt: number } | null;
  visibleTypes: Set<string>;
}

function loadCesium(): Promise<typeof import("cesium")> {
  if (typeof window === "undefined") return Promise.reject("SSR");
  if (window.Cesium) return Promise.resolve(window.Cesium);

  return new Promise((resolve, reject) => {
    window.CESIUM_BASE_URL = CESIUM_CDN;

    // Inject CSS
    if (!document.querySelector('link[data-cesium="1"]')) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = `${CESIUM_CDN}/Widgets/widgets.css`;
      link.setAttribute("data-cesium", "1");
      document.head.appendChild(link);
    }

    // Inject script
    const script = document.createElement("script");
    script.src = `${CESIUM_CDN}/Cesium.js`;
    script.async = true;
    script.onload = () => {
      if (window.Cesium) resolve(window.Cesium);
      else reject(new Error("Cesium failed to attach to window"));
    };
    script.onerror = () => reject(new Error("Failed to load Cesium from CDN"));
    document.head.appendChild(script);
  });
}

export default function Globe({ positions, onSatelliteClick, onConjunctionFocus, visibleTypes }: GlobeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const viewerRef = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const entitiesRef = useRef<Map<number, any>>(new Map());
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cesiumRef = useRef<any>(null);

  useEffect(() => {
    let mounted = true;

    (async () => {
      if (!containerRef.current) return;

      try {
        const Cesium = await loadCesium();
        if (!mounted || !containerRef.current) return;
        cesiumRef.current = Cesium;

        const ionToken = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN;
        if (ionToken) {
          Cesium.Ion.defaultAccessToken = ionToken;
        }

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const viewerOptions: any = {
          animation: false,
          baseLayerPicker: false,
          fullscreenButton: false,
          geocoder: false,
          homeButton: false,
          infoBox: false,
          sceneModePicker: false,
          selectionIndicator: true,
          timeline: false,
          navigationHelpButton: false,
          scene3DOnly: true,
          shouldAnimate: true,
        };

        if (!ionToken) {
          viewerOptions.baseLayer = Cesium.ImageryLayer.fromProviderAsync(
            Cesium.TileMapServiceImageryProvider.fromUrl(
              Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII"),
            ),
          );
        }

        const viewer = new Cesium.Viewer(containerRef.current, viewerOptions);

        viewer.scene.backgroundColor = Cesium.Color.BLACK;
        viewer.scene.globe.enableLighting = true;
        viewer.scene.globe.atmosphereLightIntensity = 10.0;

        viewer.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(0, 20, 20_000_000),
        });

        viewer.screenSpaceEventHandler.setInputAction(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (movement: any) => {
            const picked = viewer.scene.pick(movement.position);
            if (Cesium.defined(picked) && picked.id) {
              const satData = picked.id._satelliteData as SatellitePosition | undefined;
              if (satData && onSatelliteClick) onSatelliteClick(satData);
            }
          },
          Cesium.ScreenSpaceEventType.LEFT_CLICK,
        );

        viewerRef.current = viewer;
        setReady(true);
      } catch (err) {
        console.error("Globe init failed:", err);
        setError(err instanceof Error ? err.message : String(err));
      }
    })();

    return () => {
      mounted = false;
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        viewerRef.current.destroy();
        viewerRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update satellite positions
  useEffect(() => {
    const Cesium = cesiumRef.current;
    if (!ready || !Cesium || !viewerRef.current) return;

    const viewer = viewerRef.current;
    const currentEntities = entitiesRef.current;
    const activeIds = new Set<number>();

    for (const sat of positions) {
      if (!visibleTypes.has(sat.object_type)) continue;
      activeIds.add(sat.norad_cat_id);
      const color = OBJECT_TYPE_COLORS[sat.object_type] || OBJECT_TYPE_COLORS.UNKNOWN;
      const cesiumColor = Cesium.Color.fromCssColorString(color);

      const existing = currentEntities.get(sat.norad_cat_id);
      if (existing) {
        existing.position = new Cesium.ConstantPositionProperty(
          Cesium.Cartesian3.fromDegrees(sat.longitude, sat.latitude, sat.altitude_km * 1000),
        );
      } else {
        const entity = viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(
            sat.longitude, sat.latitude, sat.altitude_km * 1000,
          ),
          point: {
            pixelSize: sat.object_type === "DEBRIS" ? 2 : 4,
            color: cesiumColor,
            outlineColor: Cesium.Color.WHITE.withAlpha(0.3),
            outlineWidth: 1,
            scaleByDistance: new Cesium.NearFarScalar(1e6, 1.5, 1e8, 0.3),
          },
          label: {
            text: sat.object_name,
            font: "11px sans-serif",
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            pixelOffset: new Cesium.Cartesian2(0, -8),
            scaleByDistance: new Cesium.NearFarScalar(1e5, 1.0, 5e6, 0.0),
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 5e6),
          },
        });
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (entity as any)._satelliteData = sat;
        currentEntities.set(sat.norad_cat_id, entity);
      }
    }

    for (const [id, entity] of currentEntities) {
      if (!activeIds.has(id)) {
        viewer.entities.remove(entity);
        currentEntities.delete(id);
      }
    }
  }, [positions, ready, visibleTypes]);

  // Fly to conjunction location
  useEffect(() => {
    const Cesium = cesiumRef.current;
    if (!onConjunctionFocus || !Cesium || !viewerRef.current) return;
    viewerRef.current.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(
        onConjunctionFocus.lon,
        onConjunctionFocus.lat,
        onConjunctionFocus.alt * 1000 + 500_000,
      ),
      duration: 2,
    });
  }, [onConjunctionFocus]);

  return (
    <div ref={containerRef} className="w-full h-full relative" style={{ minHeight: "100%" }}>
      {!ready && !error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-950 text-gray-400 z-10">
          <div className="text-center">
            <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3" />
            <p>Loading 3D Globe...</p>
          </div>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-950 text-red-400 z-10 p-4">
          <div className="text-center max-w-md">
            <p className="font-semibold mb-2">Globe failed to load</p>
            <p className="text-xs text-gray-500">{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}
