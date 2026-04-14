import { render, screen } from "@testing-library/svelte";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import S3MapPreview from "../../../src/lib/components/S3MapPreview.svelte";

const fetchMock = vi.fn();

describe("S3MapPreview", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterAll(() => {
    vi.unstubAllGlobals();
  });

  it("test_shows_error_when_map_container_cannot_initialize", async () => {
    (globalThis as any).__leafletMockConfig = {
      mapReturnsNull: true,
      boundsValid: true,
    };

    render(S3MapPreview, {
      fileKey: "maps/sample.geojson",
      fileSize: 1024,
      previewUrl: "https://example.com/sample.geojson",
    });

    expect(
      await screen.findByText("Map container failed to initialize."),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("test_renders_preview_when_bounds_are_not_valid", async () => {
    (globalThis as any).__leafletMockConfig = {
      mapReturnsNull: false,
      boundsValid: false,
    };

    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              geometry: { type: "Point", coordinates: [0, 0] },
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

    render(S3MapPreview, {
      fileKey: "maps/sample.geojson",
      fileSize: 1024,
      previewUrl: "https://example.com/sample.geojson",
    });

    expect(await screen.findByText(/1 feature/i)).toBeInTheDocument();
    expect(screen.queryByText(/failed to render geospatial preview/i)).not.toBeInTheDocument();
  });
});
