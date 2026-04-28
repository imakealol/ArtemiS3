export const SUPPORTED_GEOSPATIAL_EXTENSIONS = [
  ".geojson",
  ".kml",
  ".kmz",
] as const;

export const GEOSPATIAL_SIZE_CAP_BYTES = 15 * 1024 * 1024;

export type GeospatialFormat = "geojson" | "kml" | "kmz";

export type GeoJsonGeometryType =
  | "Point"
  | "MultiPoint"
  | "LineString"
  | "MultiLineString"
  | "Polygon"
  | "MultiPolygon"
  | "GeometryCollection";

export type GeoJsonGeometry = {
  type: GeoJsonGeometryType;
  coordinates?: unknown;
  geometries?: GeoJsonGeometry[];
};

export type GeoJsonFeature = {
  type: "Feature";
  geometry: GeoJsonGeometry | null;
  properties: Record<string, unknown> | null;
  id?: string | number;
};

export type GeoJsonFeatureCollection = {
  type: "FeatureCollection";
  features: GeoJsonFeature[];
};

export type GeospatialPreviewResult = {
  format: GeospatialFormat;
  featureCollection: GeoJsonFeatureCollection;
  featureCount: number;
  geometryTypes: GeoJsonGeometryType[];
  normalization: {
    swappedCoordinateOrder: boolean;
    wrappedLongitudes: boolean;
    coordinatePairs: number;
    validCoordinateRatio: number;
  };
};
