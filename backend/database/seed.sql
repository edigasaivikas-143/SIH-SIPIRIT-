-- Clear existing data for a fresh demo run
TRUNCATE TABLE space_3d CASCADE;
TRUNCATE TABLE parcel CASCADE;

-- Insert Base 2D Parent Parcel
INSERT INTO parcel (ulpin, geometry_2d, status) 
VALUES (
    '12345678901234', 
    ST_GeomFromText('POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))'),
    'ACTIVE'
);

-- Insert Valid 3D Unit (Apartment 301)
INSERT INTO space_3d (parcel_3d_id, parent_ulpin, z_min, z_max, space_class, rights_code, unit_id, version) 
VALUES (
    '12345678901234-F03-V-PRV-A301-V01', 
    '12345678901234', 
    9.2, 
    12.4, 
    'V', 
    'PRV', 
    'A301', 
    'V01'
);

-- Insert PLANTED CONFLICT (Overlapping geometry for the live demo catch)
-- This record claims the exact same Z-space (9.2 to 12.4) as A301 above, triggering the topology intersection check live.
INSERT INTO space_3d (parcel_3d_id, parent_ulpin, z_min, z_max, space_class, rights_code, unit_id, version) 
VALUES (
    '12345678901234-F03-V-COM-TERRACE-V01', 
    '12345678901234', 
    11.0, 
    15.0, 
    'V', 
    'COM', 
    'TERRACE_CONFLICT', 
    'V01'
);
