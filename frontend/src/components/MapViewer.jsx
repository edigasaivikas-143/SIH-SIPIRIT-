import React, { useEffect, useRef, useState, useCallback } from "react";
import { Viewer, Entity, PolylineGraphics } from "resium";
import * as Cesium from "cesium";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

// Rights-code -> colour, so "private vs common vs utility vs commercial"
// is readable on the map without opening the PropertyPanel.
const RIGHTS_COLOR = {
  PRV: Cesium.Color.fromCssColorString("#4C8DFF"),
  COM: Cesium.Color.fromCssColorString("#F5A623"),
  UTL: Cesium.Color.fromCssColorString("#8E8E93"),
  CML: Cesium.Color.fromCssColorString("#34C759"),
};

const FAIL_COLOR = Cesium.Color.fromCssColorString("#FF3B30");

/**
 * MapViewer — the CesiumJS 3D viewer described in the project guide's
 * architecture table (Section 10: "React + CesiumJS ... Interactive 3D
 * map, selection, elevation filters, rights display, NL query box").
 *
 * Renders each 3D_SPACE as an extruded polygon at its z_min/z_max, colours
 * it by rights class, and flags any space with a FAIL validation as red so
 * the "live validation-catch" demo beat (Section 8) is visible on the map,
 * not just in a side panel.
 */
export default function MapViewer({ parcelId, onSelectSpace }) {
  const [spaces, setSpaces] = useState([]);
  const [loading, setLoading] = useState(false);
  const viewerRef = useRef(null);

  const loadSpaces = useCallback(async () => {
    if (!parcelId) return;
    setLoading(true);
    try {
      const { data } = await axios.get(`${API_BASE}/parcels/${parcelId}/spaces`);
      setSpaces(data);
    } catch (err) {
      console.error("Failed to load 3D spaces for parcel", parcelId, err);
    } finally {
      setLoading(false);
    }
  }, [parcelId]);

  useEffect(() => {
    loadSpaces();
  }, [loadSpaces]);

  const handleClick = (space) => {
    onSelectSpace?.(space);
  };

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      {loading && (
        <div style={{ position: "absolute", top: 8, left: 8, zIndex: 1, color: "#fff" }}>
          Loading volumetric spaces…
        </div>
      )}
      <Viewer full ref={viewerRef} timeline={false} animation={false} baseLayerPicker={false}>
        {spaces.map((space) => {
          const hierarchy = toCesiumPolygonHierarchy(space);
          if (!hierarchy) return null;
          const isFail = space.has_validation_failure;
          const color = (isFail ? FAIL_COLOR : RIGHTS_COLOR[space.rights_code] || Cesium.Color.WHITE)
            .withAlpha(0.65);

          return (
            <Entity
              key={space.parcel_3d_id}
              name={space.ulpin_3d_code || space.unit_id}
              description={`${space.unit_id} · ${space.status}`}
              onClick={() => handleClick(space)}
              polygon={{
                hierarchy,
                extrudedHeight: space.z_max,
                height: space.z_min,
                material: color,
                outline: true,
                outlineColor: isFail ? FAIL_COLOR : Cesium.Color.BLACK,
              }}
            />
          );
        })}
      </Viewer>
    </div>
  );
}

function toCesiumPolygonHierarchy(space) {
  const footprint = space?.geometry_3d?.footprint || space?.footprint;
  if (!footprint || footprint.length < 3) return null;
  const positions = footprint.flatMap(([lon, lat]) => [lon, lat]);
  return new Cesium.PolygonHierarchy(Cesium.Cartesian3.fromDegreesArray(positions));
}
