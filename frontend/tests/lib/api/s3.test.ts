import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import {
  editObjectTags,
  getRefreshStatus,
  searchS3,
  searchS3FolderChildren,
  searchS3Folders,
} from "../../../src/lib/api/s3";

const { axiosPostMock } = vi.hoisted(() => ({
  axiosPostMock: vi.fn(),
}));

vi.mock("axios", () => ({
  default: {
    post: axiosPostMock,
  },
}));

const fetchMock = vi.fn();

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

describe("s3 api client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
    axiosPostMock.mockReset();
  });

  afterAll(() => {
    vi.unstubAllGlobals();
  });

  it("test_search_s3_maps_snake_case_and_camel_case_variants", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse([
        {
          key: "folder/sample.pdf",
          size: 1024,
          last_modified: "2024-01-01T00:00:00Z",
          storage_class: "GLACIER",
          tags: ["archive"],
        },
        {
          key: "folder/second.txt",
          size: 2048,
          lastModified: "2024-02-01T00:00:00Z",
          storageClass: "STANDARD",
          tags: [],
        },
      ]),
    );

    const items = await searchS3({
      s3Uri: "s3://bucket/prefix",
      contains: "sample",
      suffixes: ["pdf", "txt"],
      storageClasses: ["STANDARD", "GLACIER"],
      sortBy: "Key",
      sortDirection: "desc",
    });

    expect(items).toEqual([
      {
        key: "folder/sample.pdf",
        size: 1024,
        lastModified: "2024-01-01T00:00:00Z",
        storageClass: "GLACIER",
        tags: ["archive"],
      },
      {
        key: "folder/second.txt",
        size: 2048,
        lastModified: "2024-02-01T00:00:00Z",
        storageClass: "STANDARD",
        tags: [],
      },
    ]);

    const request = new URL(fetchMock.mock.calls[0][0], "http://localhost");
    expect(request.pathname).toBe("/api/s3/search");
    expect(request.searchParams.get("s3_uri")).toBe("s3://bucket/prefix");
    expect(request.searchParams.getAll("suffixes")).toEqual(["pdf", "txt"]);
    expect(request.searchParams.getAll("storage_classes")).toEqual([
      "STANDARD",
      "GLACIER",
    ]);
  });

  it("test_search_s3_handles_empty_contains_and_omits_empty_arrays", async () => {
    fetchMock.mockResolvedValue(jsonResponse([]));

    await searchS3({
      s3Uri: "s3://bucket",
      contains: "",
      suffixes: [],
    });

    const request = new URL(fetchMock.mock.calls[0][0], "http://localhost");
    expect(request.searchParams.has("contains")).toBe(true);
    expect(request.searchParams.get("contains")).toBe("");
    expect(request.searchParams.has("suffixes")).toBe(false);
  });

  it("test_search_s3_returns_400_for_invalid_s3_uri", async () => {
    fetchMock.mockResolvedValue(new Response("invalid s3 uri", { status: 400 }));

    await expect(searchS3({ s3Uri: "not-an-s3-uri" } as any)).rejects.toThrow(
      "S3 search failed: 400 invalid s3 uri",
    );
  });

  it("test_search_s3_propagates_network_failure", async () => {
    fetchMock.mockRejectedValue(new Error("network down"));

    await expect(searchS3({ s3Uri: "s3://bucket" })).rejects.toThrow(
      "network down",
    );
  });

  it("test_list_s3_folder_children_normalizes_invalid_sort_direction", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        path: "folder",
        breadcrumbs: [],
        children: [],
      }),
    );

    const data = await searchS3FolderChildren({
      s3Uri: "s3://bucket",
      path: "folder",
      sortBy: "Key",
      sortDirection: "sideways" as any,
    });

    const request = new URL(fetchMock.mock.calls[0][0], "http://localhost");
    expect(request.pathname).toBe("/api/s3/folders/children");
    expect(request.searchParams.get("sort_direction")).toBe("asc");
    expect(data.files).toBeUndefined();
  });

  it("test_search_s3_folders_serializes_filters_and_returns_data", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse([
        {
          path: "folder/path",
          name: "path",
          depth: 2,
          matched_count: 5,
        },
      ]),
    );

    const folders = await searchS3Folders({
      s3Uri: "s3://bucket",
      contains: "mars",
      limit: 25,
    });

    expect(folders).toHaveLength(1);
    expect(folders[0].path).toBe("folder/path");

    const request = new URL(fetchMock.mock.calls[0][0], "http://localhost");
    expect(request.pathname).toBe("/api/s3/folders/search");
    expect(request.searchParams.get("contains")).toBe("mars");
    expect(request.searchParams.get("limit")).toBe("25");
  });

  it("test_refresh_status_returns_400_when_uri_invalid", async () => {
    fetchMock.mockResolvedValue(new Response("bad uri", { status: 400 }));

    await expect(getRefreshStatus("bad://uri")).rejects.toThrow(
      "Refresh status failed: 400 bad uri",
    );
  });

  it("test_edit_object_tags_handles_error_without_throwing", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    axiosPostMock.mockRejectedValue(new Error("api failed"));

    await expect(
      editObjectTags("bucket-name", "path/to/key.txt", ["science"]),
    ).resolves.toBeUndefined();

    expect(errorSpy).toHaveBeenCalledWith(
      "Failed to edit tags",
      expect.any(Error),
    );
    errorSpy.mockRestore();
  });
});
