import JSZip from "jszip";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import {
  getGeospatialExtensions,
  getGeospatialFormatFromKey,
  isGeospatialPreviewableKey,
  loadGeospatialPreviewFromUrl,
  normalizeGeoJsonInput,
} from "../../../src/lib/utils/geospatialPreview";
import { GEOSPATIAL_SIZE_CAP_BYTES } from "../../../src/lib/schemas/geospatial";

const fetchMock = vi.fn();

const sampleKml = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Sample Point</name>
      <Point>
        <coordinates>-122.0822035425683,37.42228990140251,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>`;

describe("geospatialPreview utils", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterAll(() => {
    vi.unstubAllGlobals();
  });

  it("test_get_geospatial_format_handles_supported_extensions", () => {
    expect(getGeospatialFormatFromKey("path/to/a.geojson")).toBe("geojson");
    expect(getGeospatialFormatFromKey("path/to/a.KML")).toBe("kml");
    expect(getGeospatialFormatFromKey("path/to/a.kmz?token=123")).toBe("kmz");
    expect(getGeospatialFormatFromKey("path/to/a.txt")).toBeNull();
    expect(isGeospatialPreviewableKey("path/to/a.geojson")).toBe(true);
    expect(isGeospatialPreviewableKey("path/to/a.txt")).toBe(false);
    expect(getGeospatialExtensions()).toEqual([".geojson", ".kml", ".kmz"]);
  });

  it("test_normalize_geojson_input_accepts_feature_collections_features_and_geometries", () => {
    const fromCollection = normalizeGeoJsonInput({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [0, 1] },
          properties: { id: 1 },
        },
      ],
    });
    expect(fromCollection.features).toHaveLength(1);

    const fromFeature = normalizeGeoJsonInput({
      type: "Feature",
      geometry: { type: "LineString", coordinates: [[0, 0], [1, 1]] },
      properties: null,
    });
    expect(fromFeature.features).toHaveLength(1);
    expect(fromFeature.features[0].geometry?.type).toBe("LineString");

    const fromGeometry = normalizeGeoJsonInput({
      type: "Polygon",
      coordinates: [[[0, 0], [1, 1], [1, 0], [0, 0]]],
    });
    expect(fromGeometry.features).toHaveLength(1);
    expect(fromGeometry.features[0].geometry?.type).toBe("Polygon");
  });

  it("test_load_geospatial_preview_parses_geojson_and_extracts_metadata", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              geometry: { type: "Point", coordinates: [100.0, 0.0] },
              properties: { name: "A" },
            },
            {
              type: "Feature",
              geometry: {
                type: "LineString",
                coordinates: [[100.0, 0.0], [101.0, 1.0]],
              },
              properties: {},
            },
          ],
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    const result = await loadGeospatialPreviewFromUrl({
      key: "folder/sample.geojson",
      size: 2048,
      previewUrl: "https://example.com/sample.geojson",
    });

    expect(result.format).toBe("geojson");
    expect(result.featureCount).toBe(2);
    expect(result.geometryTypes).toEqual(expect.arrayContaining(["Point", "LineString"]));
    expect(result.normalization.validCoordinateRatio).toBeGreaterThan(0.99);
  });

  it("test_load_geospatial_preview_rejects_malformed_geojson", async () => {
    fetchMock.mockResolvedValue(
      new Response("not-json", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(
      loadGeospatialPreviewFromUrl({
        key: "bad.geojson",
        size: 128,
        previewUrl: "https://example.com/bad.geojson",
      }),
    ).rejects.toThrow("Malformed GeoJSON file");
  });

  it("test_load_geospatial_preview_normalizes_swapped_coordinate_order", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              geometry: { type: "Point", coordinates: [10, 120] },
              properties: {},
            },
            {
              type: "Feature",
              geometry: { type: "Point", coordinates: [20, -130] },
              properties: {},
            },
          ],
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    const result = await loadGeospatialPreviewFromUrl({
      key: "swapped.geojson",
      size: 512,
      previewUrl: "https://example.com/swapped.geojson",
    });

    expect(result.normalization.swappedCoordinateOrder).toBe(true);
    expect(result.normalization.validCoordinateRatio).toBeGreaterThan(0.99);
    const first = result.featureCollection.features[0].geometry as any;
    expect(first.coordinates[0]).toBe(120);
    expect(first.coordinates[1]).toBe(10);
  });

  it("test_load_geospatial_preview_wraps_0_to_360_longitudes", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              geometry: { type: "Point", coordinates: [220, 10] },
              properties: {},
            },
            {
              type: "Feature",
              geometry: { type: "Point", coordinates: [300, -20] },
              properties: {},
            },
          ],
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    const result = await loadGeospatialPreviewFromUrl({
      key: "wrapped.geojson",
      size: 512,
      previewUrl: "https://example.com/wrapped.geojson",
    });

    expect(result.normalization.wrappedLongitudes).toBe(true);
    const first = result.featureCollection.features[0].geometry as any;
    expect(first.coordinates[0]).toBe(-140);
    expect(first.coordinates[1]).toBe(10);
  });

  it("test_load_geospatial_preview_rejects_geojson_with_no_features", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "FeatureCollection",
          features: [],
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await expect(
      loadGeospatialPreviewFromUrl({
        key: "empty.geojson",
        size: 100,
        previewUrl: "https://example.com/empty.geojson",
      }),
    ).rejects.toThrow("has no features to display");
  });

  it("test_load_geospatial_preview_rejects_unsupported_coordinate_systems", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              geometry: { type: "Point", coordinates: [500000, 200000] },
              properties: {},
            },
            {
              type: "Feature",
              geometry: { type: "Point", coordinates: [600000, 250000] },
              properties: {},
            },
          ],
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await expect(
      loadGeospatialPreviewFromUrl({
        key: "projected.geojson",
        size: 100,
        previewUrl: "https://example.com/projected.geojson",
      }),
    ).rejects.toThrow("unsupported reference system");
  });

  it("test_load_geospatial_preview_parses_kml", async () => {
    fetchMock.mockResolvedValue(
      new Response(sampleKml, {
        status: 200,
        headers: { "Content-Type": "application/vnd.google-earth.kml+xml" },
      }),
    );

    const result = await loadGeospatialPreviewFromUrl({
      key: "sample.kml",
      size: 512,
      previewUrl: "https://example.com/sample.kml",
    });

    expect(result.format).toBe("kml");
    expect(result.featureCount).toBeGreaterThan(0);
  });

  it("test_load_geospatial_preview_rejects_malformed_kml", async () => {
    fetchMock.mockResolvedValue(
      new Response("<kml><broken>", {
        status: 200,
        headers: { "Content-Type": "application/xml" },
      }),
    );

    await expect(
      loadGeospatialPreviewFromUrl({
        key: "broken.kml",
        size: 100,
        previewUrl: "https://example.com/broken.kml",
      }),
    ).rejects.toThrow("Malformed KML file");
  });

  it("test_load_geospatial_preview_parses_kmz", async () => {
    const zip = new JSZip();
    zip.file("doc.kml", sampleKml);
    const kmzBuffer = await zip.generateAsync({ type: "arraybuffer" });

    fetchMock.mockResolvedValue(
      new Response(kmzBuffer, {
        status: 200,
      }),
    );

    const result = await loadGeospatialPreviewFromUrl({
      key: "sample.kmz",
      size: 1024,
      previewUrl: "https://example.com/sample.kmz",
    });

    expect(result.format).toBe("kmz");
    expect(result.featureCount).toBeGreaterThan(0);
  });

  it("test_load_geospatial_preview_rejects_kmz_without_kml", async () => {
    const zip = new JSZip();
    zip.file("notes.txt", "not-kml");
    const kmzBuffer = await zip.generateAsync({ type: "arraybuffer" });

    fetchMock.mockResolvedValue(
      new Response(kmzBuffer, {
        status: 200,
      }),
    );

    await expect(
      loadGeospatialPreviewFromUrl({
        key: "sample.kmz",
        size: 1024,
        previewUrl: "https://example.com/sample.kmz",
      }),
    ).rejects.toThrow("KMZ file has no embedded KML document");
  });

  it("test_load_geospatial_preview_rejects_over_size_limit", async () => {
    await expect(
      loadGeospatialPreviewFromUrl({
        key: "huge.geojson",
        size: GEOSPATIAL_SIZE_CAP_BYTES + 1,
        previewUrl: "https://example.com/huge.geojson",
      }),
    ).rejects.toThrow("exceeds the 15 MB preview limit");

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("test_load_geospatial_preview_rejects_unsupported_format", async () => {
    await expect(
      loadGeospatialPreviewFromUrl({
        key: "sample.txt",
        size: 100,
        previewUrl: "https://example.com/sample.txt",
      }),
    ).rejects.toThrow("not supported for map preview");
  });

  it("test_load_geospatial_preview_handles_fetch_failures", async () => {
    fetchMock.mockRejectedValue(new Error("offline"));

    await expect(
      loadGeospatialPreviewFromUrl({
        key: "sample.geojson",
        size: 100,
        previewUrl: "https://example.com/sample.geojson",
      }),
    ).rejects.toThrow("Could not fetch geospatial preview from S3");
  });

  it("test_load_geospatial_preview_handles_non_ok_responses", async () => {
    fetchMock.mockResolvedValue(new Response("forbidden", { status: 403 }));

    await expect(
      loadGeospatialPreviewFromUrl({
        key: "sample.geojson",
        size: 100,
        previewUrl: "https://example.com/sample.geojson",
      }),
    ).rejects.toThrow("Could not fetch geospatial preview (403)");
  });

  it("test_load_geospatial_preview_wraps_non_geospatial_parse_errors", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      text: async () => {
        throw new Error("unexpected reader error");
      },
      arrayBuffer: async () => new ArrayBuffer(0),
    } as Response);

    await expect(
      loadGeospatialPreviewFromUrl({
        key: "sample.geojson",
        size: 100,
        previewUrl: "https://example.com/sample.geojson",
      }),
    ).rejects.toThrow("Failed to parse geospatial file");
  });

  it("test_normalize_geojson_input_rejects_invalid_structures", () => {
    expect(() => normalizeGeoJsonInput("bad-input")).toThrow(
      "Unsupported geospatial content",
    );

    expect(() =>
      normalizeGeoJsonInput({
        type: "FeatureCollection",
        features: "wrong-type",
      }),
    ).toThrow("missing features");

    expect(() =>
      normalizeGeoJsonInput({
        type: "Feature",
        geometry: { type: "Point" },
        properties: null,
      }),
    ).toThrow("Invalid geometry");
  });
});
