import { render, screen, waitFor } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import S3FolderExplorer from "../../../src/lib/components/S3FolderExplorer.svelte";

const fetchMock = vi.fn();

describe("S3FolderExplorer", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterAll(() => {
    vi.unstubAllGlobals();
  });

  it("test_open_folder_calls_callback_and_updates_selected_folder", async () => {
    const user = userEvent.setup();
    const onOpenFolder = vi.fn().mockResolvedValue(undefined);

    render(S3FolderExplorer, {
      searchedYet: true,
      loading: false,
      s3Uri: "s3://bucket",
      suggestions: [
        { path: "missions/mars", name: "mars", depth: 1, matched_count: 8 },
      ],
      children: [],
      files: [],
      breadcrumbs: [],
      activePath: "",
      sortBy: undefined,
      sortDirection: "asc",
      onOpenFolder,
      onOpenBreadcrumb: vi.fn(),
      onNavigateUp: vi.fn(),
      onSort: vi.fn(),
      onDownload: vi.fn(),
    });

    const folderButton = screen.getByRole("button", { name: /missions\/mars/i });
    await user.click(folderButton);

    expect(onOpenFolder).toHaveBeenCalledWith("missions/mars");
    expect(folderButton.className).toContain("border-amber-300/50");
  });

  it("test_handle_preview_shows_error_when_preview_url_missing", async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({}), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(S3FolderExplorer, {
      searchedYet: true,
      loading: false,
      s3Uri: "s3://bucket",
      suggestions: [{ path: "missions", name: "missions", depth: 1, matched_count: 1 }],
      children: [],
      files: [
        {
          key: "missions/sample.png",
          size: 100,
          lastModified: "2025-01-01T00:00:00Z",
          storageClass: "STANDARD",
          tags: [],
        },
      ],
      breadcrumbs: [],
      activePath: "missions",
      sortBy: undefined,
      sortDirection: "asc",
      onOpenFolder: vi.fn(),
      onOpenBreadcrumb: vi.fn(),
      onNavigateUp: vi.fn(),
      onSort: vi.fn(),
      onDownload: vi.fn(),
    });

    await user.click(screen.getByTitle("Preview"));

    expect(
      await screen.findByText("Preview URL was not returned by the server."),
    ).toBeInTheDocument();
  });

  it("test_preview_shows_error_for_invalid_s3_uri", async () => {
    const user = userEvent.setup();

    render(S3FolderExplorer, {
      searchedYet: true,
      loading: false,
      s3Uri: "not-an-s3-uri",
      suggestions: [{ path: "missions", name: "missions", depth: 1, matched_count: 1 }],
      children: [],
      files: [
        {
          key: "missions/sample.png",
          size: 100,
          lastModified: "2025-01-01T00:00:00Z",
          storageClass: "STANDARD",
          tags: [],
        },
      ],
      breadcrumbs: [],
      activePath: "missions",
      sortBy: undefined,
      sortDirection: "asc",
      onOpenFolder: vi.fn(),
      onOpenBreadcrumb: vi.fn(),
      onNavigateUp: vi.fn(),
      onSort: vi.fn(),
      onDownload: vi.fn(),
    });

    await user.click(screen.getByTitle("Preview"));

    expect(
      await screen.findByText("Invalid S3 URI for preview."),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("test_clear_preview_when_selected_file_is_removed_from_files", async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ preview_url: "https://example.com/preview.png" }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    const view = render(S3FolderExplorer, {
      searchedYet: true,
      loading: false,
      s3Uri: "s3://bucket",
      suggestions: [{ path: "missions", name: "missions", depth: 1, matched_count: 1 }],
      children: [],
      files: [
        {
          key: "missions/sample.png",
          size: 100,
          lastModified: "2025-01-01T00:00:00Z",
          storageClass: "STANDARD",
          tags: [],
        },
      ],
      breadcrumbs: [],
      activePath: "missions",
      sortBy: undefined,
      sortDirection: "asc",
      onOpenFolder: vi.fn(),
      onOpenBreadcrumb: vi.fn(),
      onNavigateUp: vi.fn(),
      onSort: vi.fn(),
      onDownload: vi.fn(),
    });

    await user.click(screen.getByTitle("Preview"));
    expect(await screen.findByText("Preview: missions/sample.png")).toBeInTheDocument();

    await view.rerender({
      searchedYet: true,
      loading: false,
      s3Uri: "s3://bucket",
      suggestions: [{ path: "missions", name: "missions", depth: 1, matched_count: 1 }],
      children: [],
      files: [],
      breadcrumbs: [],
      activePath: "missions",
      sortBy: undefined,
      sortDirection: "asc",
      onOpenFolder: vi.fn(),
      onOpenBreadcrumb: vi.fn(),
      onNavigateUp: vi.fn(),
      onSort: vi.fn(),
      onDownload: vi.fn(),
    });

    await waitFor(() => {
      expect(screen.queryByText("Preview: missions/sample.png")).not.toBeInTheDocument();
    });
  });

  it("test_geojson_preview_renders_map_preview_branch", async () => {
    const user = userEvent.setup();
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ preview_url: "https://example.com/missions.geojson" }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            type: "FeatureCollection",
            features: [
              {
                type: "Feature",
                geometry: { type: "Point", coordinates: [10, 11] },
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

    render(S3FolderExplorer, {
      searchedYet: true,
      loading: false,
      s3Uri: "s3://bucket",
      suggestions: [{ path: "missions", name: "missions", depth: 1, matched_count: 1 }],
      children: [],
      files: [
        {
          key: "missions/footprint.geojson",
          size: 1024,
          lastModified: "2025-01-01T00:00:00Z",
          storageClass: "STANDARD",
          tags: [],
        },
      ],
      breadcrumbs: [],
      activePath: "missions",
      sortBy: undefined,
      sortDirection: "asc",
      onOpenFolder: vi.fn(),
      onOpenBreadcrumb: vi.fn(),
      onNavigateUp: vi.fn(),
      onSort: vi.fn(),
      onDownload: vi.fn(),
    });

    await user.click(screen.getByTitle("Preview"));

    expect(await screen.findByText(/Map preview: footprint.geojson/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("test_geojson_preview_shows_size_limit_error_for_large_file", async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ preview_url: "https://example.com/huge.geojson" }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    render(S3FolderExplorer, {
      searchedYet: true,
      loading: false,
      s3Uri: "s3://bucket",
      suggestions: [{ path: "missions", name: "missions", depth: 1, matched_count: 1 }],
      children: [],
      files: [
        {
          key: "missions/huge.geojson",
          size: 16 * 1024 * 1024,
          lastModified: "2025-01-01T00:00:00Z",
          storageClass: "STANDARD",
          tags: [],
        },
      ],
      breadcrumbs: [],
      activePath: "missions",
      sortBy: undefined,
      sortDirection: "asc",
      onOpenFolder: vi.fn(),
      onOpenBreadcrumb: vi.fn(),
      onNavigateUp: vi.fn(),
      onSort: vi.fn(),
      onDownload: vi.fn(),
    });

    await user.click(screen.getByTitle("Preview"));

    expect(
      await screen.findByText(/exceeds the 15 MB preview limit/i),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
