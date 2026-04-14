import { describe, expect, it } from "vitest";
import { prepareFeatureCollectionForRendering } from "../../../src/lib/utils/geospatialRenderPrep";
import type { GeoJsonFeatureCollection } from "../../../src/lib/schemas/geospatial";

function makePointFeature(index: number) {
  return {
    type: "Feature" as const,
    geometry: {
      type: "Point" as const,
      coordinates: [index % 180, (index % 90) - 45],
    },
    properties: { id: index },
  };
}

describe("geospatialRenderPrep", () => {
  it("test_keeps_small_collections_without_sampling", () => {
    const source: GeoJsonFeatureCollection = {
      type: "FeatureCollection",
      features: [
        makePointFeature(1),
        {
          type: "Feature",
          geometry: {
            type: "LineString",
            coordinates: [
              [10, 10],
              [20, 20],
              [30, 30],
            ],
          },
          properties: {},
        },
      ],
    };

    const prepared = prepareFeatureCollectionForRendering(source);
    expect(prepared.sampledPoints).toBe(false);
    expect(prepared.sampledLines).toBe(false);
    expect(prepared.renderedPointFeatures).toBe(1);
    expect(prepared.renderedLineFeatures).toBe(1);
  });

  it("test_samples_large_point_collections", () => {
    const source: GeoJsonFeatureCollection = {
      type: "FeatureCollection",
      features: Array.from({ length: 20000 }, (_, index) => makePointFeature(index)),
    };

    const prepared = prepareFeatureCollectionForRendering(source);
    expect(prepared.sampledPoints).toBe(true);
    expect(prepared.renderedPointFeatures).toBeLessThanOrEqual(12000);
    expect(prepared.sourcePointFeatures).toBe(20000);
  });

  it("test_simplifies_large_line_and_polygon_geometries", () => {
    const longLine = Array.from({ length: 1000 }, (_, index) => [index * 0.1, index * 0.05]);
    const longRing = Array.from({ length: 1000 }, (_, index) => [index * 0.05, index * 0.03]);
    const source: GeoJsonFeatureCollection = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: { type: "LineString", coordinates: longLine },
          properties: {},
        },
        {
          type: "Feature",
          geometry: { type: "Polygon", coordinates: [longRing] },
          properties: {},
        },
      ],
    };

    const prepared = prepareFeatureCollectionForRendering(source);
    expect(prepared.simplifiedGeometries).toBeGreaterThan(0);
    expect(prepared.renderedLineFeatures).toBe(2);
  });
});
