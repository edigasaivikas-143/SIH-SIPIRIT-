def detect_underground_volumes(dem_z_level, point_cloud):
    # Heuristic fallback: Filter points below the Digital Elevation zero-plane
    underground_pts = [p for p in point_cloud if p['z'] < dem_z_level]
    return {"space_class": "U", "confidence": 0.85, "points": underground_pts}
