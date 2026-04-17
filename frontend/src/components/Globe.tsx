"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { SatellitePosition } from "@/lib/types";
import { OBJECT_TYPE_COLORS } from "@/lib/types";

// Cesium is loaded dynamically to avoid SSR issues
let Cesium: typeof import("cesium") | null = null;

interface GlobeProps {
  positions: SatellitePosition[];
  onSatelliteClick?: (satellite: SatellitePosition) => void;
  onConjunctionFocus?: { lat: number; lon: number; alt: number } | null;
  visibleTypes: Set<string>;
}

export default function Globe({ positions, onSatelliteClick, onConjunctionFocus, visibleTypes }: GlobeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<InstanceType<typeof import("cesium").Viewer> | null>(null);
  const entitiesRef = useRef<Map<number, InstanceType<typeof import("cesium").Entity>>>(new Map());
  const [ready, setReady] = useState(false);

  // Initialize Cesium viewer
  useEffect(() => {
    let mounted = true;

    async function init() {
      if (!containerRef.current) return;

      try {
        // CRITICAL: set CESIUM_BASE_URL on window BEFORE importing cesium.
        // Cesium reads this at import time to locate Workers/Assets/Widgets.
        (window as unknown as Record<string, unknown>).CESIUM_BASE_URL = "/cesium/";

        const cesiumModule = await import("cesium");
        Cesium = cesiumModule;

        // Import Cesium CSS
        await import("cesium/Build/Cesium/Widgets/widgets.css");

        if (!mounted || !containerRef.current) return;

        // Configure Ion token if available
        const ionToken = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN;
        if (ionToken) {
          Cesium.Ion.defaultAccessToken = ionToken;
        }

        // Build viewer options. If no Ion token, use local Natural Earth tiles.
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
          // No Ion token — use locally-hosted Natural Earth imagery
          viewerOptions.baseLayer = Cesium.ImageryLayer.fromProviderAsync(
            Cesium.TileMapServiceImageryProvider.fromUrl(
              Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII"),
            ),
          );
        }

        const viewer = new Cesium.Viewer(containerRef.current, viewerOptions);

      // Dark space background
      viewer.scene.backgroundColor = Cesium.Color.BLACK;
      viewer.scene.globe.enableLighting = true;
      viewer.scene.globe.atmosphereLightIntensity = 10.0;

      // Set default camera view
      viewer.camera.setView({
        destination: Cesium.Cartesian3.fromDegrees(0, 20, 20_000_000),
      });

      // Click handler for satellite selection
      viewer.screenSpaceEventHandler.setInputAction(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (movement: any) => {
          const picked = viewer.scene.pick(movement.position);
          if (Cesium && Cesium.defined(picked) && picked.id) {
            const entity = picked.id;
            const satData = entity._satelliteData as SatellitePosition | undefined;
            if (satData && onSatelliteClick) {
              onSatelliteClick(satData);
            }
          }
        },
        Cesium.ScreenSpaceEventType.LEFT_CLICK,
      );

        viewerRef.current = viewer;
        setReady(true);
      } catch (err) {
        console.error("Globe init failed:", err);
      }
    }

    init();

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
    if (!ready || !Cesium || !viewerRef.current) return;

    const viewer = viewerRef.current;
    const currentEntities = entitiesRef.current;

    // Track which satellites are in the current update
    const activeIds = new Set<number>();

    for (const sat of positions) {
      if (!visibleTypes.has(sat.object_type)) continue;

      activeIds.add(sat.norad_cat_id);
      const color = OBJECT_TYPE_COLORS[sat.object_type] || OBJECT_TYPE_COLORS.UNKNOWN;
      const cesiumColor = Cesium.Color.fromCssColorString(color);

      const existing = currentEntities.get(sat.norad_cat_id);
      if (existing) {
        // Update position
        existing.position = new Cesium.ConstantPositionProperty(
          Cesium.Cartesian3.fromDegrees(sat.longitude, sat.latitude, sat.altitude_km * 1000)
        );
      } else {
        // Create new entity
        const entity = viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(
            sat.longitude, sat.latitude, sat.altitude_km * 1000
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

        // Attach satellite data for click handling
        (entity as unknown as Record<string, unknown>)._satelliteData = sat;
        currentEntities.set(sat.norad_cat_id, entity);
      }
    }

    // Remove entities no longer in view
    for (const [id, entity] of currentEntities) {
      if (!activeIds.has(id)) {
        viewer.entities.remove(entity);
        currentEntities.delete(id);
      }
    }
  }, [positions, ready, visibleTypes]);

  // Fly to conjunction location when requested
  useEffect(() => {
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
    <div ref={containerRef} className="w-full h-full" style={{ minHeight: "100%" }}>
      {!ready && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-950 text-gray-400 z-10">
          <div className="text-center">
            <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3" />
            <p>Loading 3D Globe...</p>
          </div>
        </div>
      )}
    </div>
  );
}
