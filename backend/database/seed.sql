-- Insert Base 2D Parcel
INSERT INTO parcel (ulpin, geometry_2d) 
VALUES ('12345678901234', ST_GeomFromText('POLYGON((...))'));

-- Insert Valid Unit (A301)
INSERT INTO space_3d (parcel_3d_id, parent_ulpin, z_min, z_max, space_class, unit_id) 
VALUES ('12345678901234-F03-V-PRV-A301-V01', '12345678901234', 9.2, 12.4, 'V', 'A301');

-- Insert PLANTED CONFLICT (Overlapping geometry for the live demo catch)
INSERT INTO space_3d (parcel_3d_id, parent_ulpin, z_min, z_max, space_class, unit_id) 
VALUES ('12345678901234-R00-V-PRV-A301-V02', '12345678901234', 11.0, 15.0, 'V', 'TERRACE_CONFLICT');
