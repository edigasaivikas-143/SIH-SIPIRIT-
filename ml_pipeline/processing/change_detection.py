  def detect_changes(historical_geom, new_geom, tolerance=0.15):
    # Compares volumes to flag unapproved extensions
    overlap = historical_geom.intersection(new_geom)
    if overlap.volume < (new_geom.volume - tolerance):
        return "CHANGE_DETECTED_ENCROACHMENT"
    return "NO_CHANGE"
