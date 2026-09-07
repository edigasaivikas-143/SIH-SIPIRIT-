def detect_underground_volumes(dem_z_level: float, point_cloud: list) -> dict:
    """
    Module D: Detects subterranean features (basements, parking) by comparing 
    spatial points against the local Digital Elevation Model (DEM) zero-plane.
    """
    underground_pts = [p for p in point_cloud if p['z'] < dem_z_level]
    
    if not underground_pts:
        return {"space_class": "None", "confidence": 1.0, "points": []}
        
    return {
        "space_class": "U", # U = Underground
        "confidence": 0.85, 
        "z_min": min(p['z'] for p in underground_pts),
        "z_max": dem_z_level,
        "points": underground_pts
    }
