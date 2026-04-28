import { describe, expect, it } from "vitest";
import {
  detectPlanetBodyFromKey,
  getPlanetProfileForKey,
  isLikelyPlanetaryButUnsupported,
} from "../../../src/lib/utils/planetProfile";

describe("planetProfile utils", () => {
  it("test_detect_planet_body_from_key_returns_mars_or_moon_or_earth", () => {
    expect(detectPlanetBodyFromKey("pigpen/mars/craters/file.kmz")).toBe("mars");
    expect(detectPlanetBodyFromKey("archive/lunar_catalog/sample.kml")).toBe("moon");
    expect(detectPlanetBodyFromKey("earth/tectonics/sample.geojson")).toBe("earth");
  });

  it("test_get_planet_profile_for_key_returns_planet_specific_tiles", () => {
    const mars = getPlanetProfileForKey("pigpen/mars/sample.kmz");
    const moon = getPlanetProfileForKey("lunar/coverage/sample.kml");
    const earth = getPlanetProfileForKey("earth/sample.geojson");

    expect(mars.label).toBe("Mars");
    expect(mars.tileUrl).toContain("opm-mars-basemap");
    expect(moon.label).toBe("Moon");
    expect(moon.tileUrl).toContain("opm-moon-basemap");
    expect(earth.label).toBe("Earth");
    expect(earth.tileUrl).toContain("openstreetmap.org");
  });

  it("test_is_likely_planetary_but_unsupported_flags_other_bodies", () => {
    expect(isLikelyPlanetaryButUnsupported("mercury/global_map.kmz")).toBe(true);
    expect(isLikelyPlanetaryButUnsupported("venus/tiles/data.kml")).toBe(true);
    expect(isLikelyPlanetaryButUnsupported("mars/crater_index.kmz")).toBe(false);
    expect(isLikelyPlanetaryButUnsupported("moon/landing_sites.kml")).toBe(false);
    expect(isLikelyPlanetaryButUnsupported("earth/roads.geojson")).toBe(false);
  });
});
