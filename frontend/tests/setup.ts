import { cleanup } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";

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

afterEach(() => {
  cleanup();
});
