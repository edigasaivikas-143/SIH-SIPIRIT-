-- 3D ULPIN Generation & Vertical Property Mapping
-- PostGIS schema implementing the volumetric cadastre model
-- (Project Guide, Sections 9 & 10: PARCEL -> STRUCTURE -> FLOOR -> 3D_SPACE -> RIGHTS,
--  plus SOURCE / VALIDATION / VERSION side tables)

CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================
-- PARCEL: the official/source ULPIN parent parcel
-- ============================================================
CREATE TABLE parcel (
    parcel_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_ulpin    VARCHAR(14) NOT NULL,   -- official 14-char ULPIN (Dept. of Land Resources)
    geometry_2d     GEOMETRY(POLYGON, 4326) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_parcel_geom ON parcel USING GIST (geometry_2d);
CREATE INDEX idx_parcel_ulpin ON parcel (parent_ulpin);

-- ============================================================
-- STRUCTURE: a building/campus sitting on a parcel
-- ============================================================
CREATE TABLE structure (
    structure_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parcel_id       UUID NOT NULL REFERENCES parcel(parcel_id) ON DELETE CASCADE,
    name            VARCHAR(120),
    footprint       GEOMETRY(POLYGON, 4326),
    height_m        NUMERIC(6,2),
    source_id       UUID,   -- FK to source, added below after source table exists
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_structure_footprint ON structure USING GIST (footprint);

-- ============================================================
-- FLOOR: vertical tiers within a structure
-- ============================================================
CREATE TABLE floor (
    floor_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    structure_id    UUID NOT NULL REFERENCES structure(structure_id) ON DELETE CASCADE,
    z_level         VARCHAR(10) NOT NULL,   -- F03 / B01 / G00 / R00
    z_min           NUMERIC(8,3) NOT NULL,
    z_max           NUMERIC(8,3) NOT NULL,
    CONSTRAINT chk_floor_z_order CHECK (z_max > z_min)
);
CREATE INDEX idx_floor_structure ON floor (structure_id);

-- ============================================================
-- 3D_SPACE: the core volumetric cadastral object.
-- This is what gets a 3D ULPIN extension code:
--   [Parent ULPIN]-[Z-Level]-[Space Class]-[Rights/Use Code]-[Unit ID]-[Version]
-- ============================================================
CREATE TABLE space_3d (
    parcel_3d_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ulpin_3d_code   VARCHAR(64) UNIQUE,             -- generated code, e.g. 12345678901234-F03-V-PRV-A301-V01
    parcel_id       UUID NOT NULL REFERENCES parcel(parcel_id) ON DELETE CASCADE,
    structure_id    UUID REFERENCES structure(structure_id) ON DELETE SET NULL,
    floor_id        UUID REFERENCES floor(floor_id) ON DELETE SET NULL,

    space_class     VARCHAR(1) NOT NULL CHECK (space_class IN ('V','S','U','E')), -- Vertical/Surface/Underground/Elevated
    rights_code     VARCHAR(3) NOT NULL,            -- PRV / COM / UTL / CML
    unit_id         VARCHAR(20) NOT NULL,           -- A301 / PRK01 / TRC01 ...
    version         INT NOT NULL DEFAULT 1,

    geometry_3d     GEOMETRY(POLYHEDRALSURFACEZ, 4326),  -- volumetric solid
    crs             VARCHAR(64) NOT NULL DEFAULT 'EPSG:4326',
    vertical_datum  VARCHAR(64) NOT NULL DEFAULT 'WGS84_ELLIPSOIDAL',
    z_min           NUMERIC(8,3) NOT NULL,
    z_max           NUMERIC(8,3) NOT NULL,

    status          VARCHAR(30) NOT NULL DEFAULT 'AI_GENERATED',
        -- AI_GENERATED -> QA_PASSED -> SURVEY_REVIEW -> APPROVED -> PUBLISHED
    confidence      NUMERIC(5,2),                   -- 0-100, from Module F confidence scoring

    predecessor_id  UUID REFERENCES space_3d(parcel_3d_id),
    valid_from      TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to        TIMESTAMPTZ,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_space3d_parcel ON space_3d (parcel_id);
CREATE INDEX idx_space3d_status ON space_3d (status);
CREATE INDEX idx_space3d_geom ON space_3d USING GIST (geometry_3d);

-- ============================================================
-- RIGHTS: ownership/lease/easement/common/utility/access records,
-- kept separate from geometry (Section 5 & 9)
-- ============================================================
CREATE TABLE rights (
    right_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parcel_3d_id    UUID NOT NULL REFERENCES space_3d(parcel_3d_id) ON DELETE CASCADE,
    party_id        VARCHAR(64) NOT NULL,           -- owner/lessee/authority identifier
    right_type      VARCHAR(20) NOT NULL CHECK (
                        right_type IN ('OWNERSHIP','LEASE','EASEMENT','COMMON','UTILITY','ACCESS','DEVELOPMENT')
                    ),
    valid_from      DATE NOT NULL,
    valid_to        DATE,
    source_document VARCHAR(255),
    active          BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX idx_rights_space ON rights (parcel_3d_id);
CREATE INDEX idx_rights_active ON rights (parcel_3d_id) WHERE active;

-- ============================================================
-- SOURCE: provenance for any input evidence (drone/LiDAR/BIM/CORS/DEM)
-- ============================================================
CREATE TABLE source (
    source_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type     VARCHAR(30) NOT NULL CHECK (
                        source_type IN ('DRONE_IMAGERY','LIDAR','GIS_PARCEL','FLOOR_PLAN_BIM','GNSS_CORS','DEM_DSM','SYNTHETIC')
                    ),
    survey_date     DATE,
    method          VARCHAR(120),
    accuracy_m      NUMERIC(6,3),
    processing_version VARCHAR(20),
    file_path       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE structure ADD CONSTRAINT fk_structure_source
    FOREIGN KEY (source_id) REFERENCES source(source_id) DEFERRABLE INITIALLY DEFERRED;

-- link space_3d to the sources that produced it (many-to-many)
CREATE TABLE space_3d_source (
    parcel_3d_id    UUID NOT NULL REFERENCES space_3d(parcel_3d_id) ON DELETE CASCADE,
    source_id       UUID NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    PRIMARY KEY (parcel_3d_id, source_id)
);

-- ============================================================
-- VALIDATION: topology / geometry / survey QC results (Section 8)
-- ============================================================
CREATE TABLE validation (
    validation_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parcel_3d_id    UUID NOT NULL REFERENCES space_3d(parcel_3d_id) ON DELETE CASCADE,
    rule            VARCHAR(40) NOT NULL CHECK (
                        rule IN ('INTERSECTION','CONTAINMENT','ADJACENCY','FLOOR_ORDERING',
                                 'GEOMETRY_VALIDITY','RIGHTS_CONSISTENCY','SURVEY_TOLERANCE','PROVENANCE_COMPLETENESS')
                    ),
    result          VARCHAR(10) NOT NULL CHECK (result IN ('PASS','FAIL','WARN')),
    tolerance       NUMERIC(8,3),
    detail          TEXT,               -- e.g. "overlaps Apartment 201, Z 9.2-9.4 m"
    conflicting_id  UUID REFERENCES space_3d(parcel_3d_id),
    reviewer        VARCHAR(64),
    confidence      NUMERIC(5,2),
    "timestamp"     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_validation_space ON validation (parcel_3d_id);
CREATE INDEX idx_validation_result ON validation (result);

-- ============================================================
-- VERSION LOG: explicit lineage for subdivision/merger/change (Section 9)
-- ============================================================
CREATE TABLE version_log (
    log_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_id       UUID NOT NULL REFERENCES space_3d(parcel_3d_id),
    version         INT NOT NULL,
    predecessor     UUID REFERENCES space_3d(parcel_3d_id),
    successor       UUID REFERENCES space_3d(parcel_3d_id),
    change_reason   VARCHAR(255),
    changed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- RERA carpet-area verification (Section 9 "NEW" use case)
-- ============================================================
CREATE TABLE rera_check (
    check_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parcel_3d_id        UUID NOT NULL REFERENCES space_3d(parcel_3d_id) ON DELETE CASCADE,
    declared_carpet_m2  NUMERIC(8,2) NOT NULL,
    measured_carpet_m2  NUMERIC(8,2) NOT NULL,
    confidence          NUMERIC(5,2) NOT NULL,
    checked_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Convenience view: everything needed to render the PropertyPanel in one query
CREATE VIEW space_3d_detail AS
SELECT
    s.parcel_3d_id,
    s.ulpin_3d_code,
    p.parent_ulpin,
    s.space_class,
    s.rights_code,
    s.unit_id,
    s.version,
    s.z_min,
    s.z_max,
    s.status,
    s.confidence,
    (SELECT COUNT(*) FROM rights r WHERE r.parcel_3d_id = s.parcel_3d_id AND r.active) AS active_rights_count,
    (SELECT bool_or(v.result = 'FAIL') FROM validation v WHERE v.parcel_3d_id = s.parcel_3d_id) AS has_validation_failure
FROM space_3d s
JOIN parcel p ON p.parcel_id = s.parcel_id;
