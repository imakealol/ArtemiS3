import { cleanup } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";

type LeafletMockConfig = {
  mapReturnsNull: boolean;
  boundsValid: boolean;
};

declare global {
  var __leafletMockConfig: LeafletMockConfig | undefined;
}

const createLeafletMockConfig = (): LeafletMockConfig => ({
  mapReturnsNull: false,
  boundsValid: true,
});

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();

  return {
    get length() {
      return values.size;
    },
    clear() {
      values.clear();
    },
    getItem(key: string) {
      return values.has(key) ? values.get(key)! : null;
    },
    key(index: number) {
      return Array.from(values.keys())[index] ?? null;
    },
    removeItem(key: string) {
      values.delete(key);
    },
    setItem(key: string, value: string) {
      values.set(String(key), String(value));
    },
  };
}

function hasUsableStorage(value: unknown): value is Storage {
  const candidate = value as Partial<Storage> | null | undefined;
  return Boolean(
    candidate &&
      typeof candidate.getItem === "function" &&
      typeof candidate.setItem === "function" &&
      typeof candidate.removeItem === "function" &&
      typeof candidate.clear === "function",
  );
}

function ensureStorage(name: "localStorage" | "sessionStorage") {
  if (hasUsableStorage(globalThis[name])) return;

  const replacement = createMemoryStorage();
  Object.defineProperty(globalThis, name, {
    configurable: true,
    writable: true,
    value: replacement,
  });

  if (typeof window !== "undefined") {
    Object.defineProperty(window, name, {
      configurable: true,
      writable: true,
      value: replacement,
    });
  }
}

ensureStorage("localStorage");
ensureStorage("sessionStorage");
globalThis.__leafletMockConfig = createLeafletMockConfig();

vi.mock("leaflet", () => {
  const getConfig = () => globalThis.__leafletMockConfig ?? createLeafletMockConfig();

  const createBounds = () => {
    const config = getConfig();
    const bounds = {
      isValid: () => config.boundsValid,
      pad: () => bounds,
    };
    return bounds;
  };

  return {
    default: {
      map: () => {
        const config = getConfig();
        if (config.mapReturnsNull) return null;
        return {
          setView: () => undefined,
          fitBounds: () => undefined,
          invalidateSize: () => undefined,
          removeLayer: () => undefined,
          remove: () => undefined,
        };
      },
      tileLayer: () => ({
        addTo: () => undefined,
      }),
      geoJSON: () => ({
        addTo: () => undefined,
        getBounds: () => createBounds(),
      }),
      circleMarker: () => ({}),
    },
  };
});

afterEach(() => {
  globalThis.__leafletMockConfig = createLeafletMockConfig();
  cleanup();
});
