from shapely.geometry import Polygon

def detect_changes(historical_geom: Polygon, new_geom: Polygon, tolerance: float = 0.15) -> str:
    """
    Module E: Compares newly surveyed 2D footprints or 3D volumes against historical 
    records to flag unapproved extensions or demolition.
    """
    if historical_geom.equals_exact(new_geom, tolerance):
        return "NO_CHANGE"
        
    overlap = historical_geom.intersection(new_geom)
    
    # If the new geometry is significantly larger than the overlap, it's an extension
    if overlap.area < (new_geom.area - tolerance):
        return "CHANGE_DETECTED_ENCROACHMENT"
        
    # If the historical geometry is significantly larger than the overlap, it's a demolition/reduction
    if overlap.area < (historical_geom.area - tolerance):
        return "CHANGE_DETECTED_REDUCTION"
        
    return "GEOMETRY_MODIFIED"
