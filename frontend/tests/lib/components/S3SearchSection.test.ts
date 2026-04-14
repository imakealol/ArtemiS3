import { render, screen, waitFor } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import S3SearchSection from "../../../src/lib/components/S3SearchSection.svelte";

const {
  searchS3Mock,
  searchS3FoldersMock,
  searchS3FolderChildrenMock,
  editObjectTagsMock,
  getRefreshStatusMock,
} = vi.hoisted(() => ({
  searchS3Mock: vi.fn(),
  searchS3FoldersMock: vi.fn(),
  searchS3FolderChildrenMock: vi.fn(),
  editObjectTagsMock: vi.fn(),
  getRefreshStatusMock: vi.fn(),
}));

vi.mock("../../../src/lib/api/s3", () => ({
  searchS3: searchS3Mock,
  searchS3Folders: searchS3FoldersMock,
  searchS3FolderChildren: searchS3FolderChildrenMock,
  editObjectTags: editObjectTagsMock,
  getRefreshStatus: getRefreshStatusMock,
}));

const QUERY_KEY = "artemis_recent_queries";
const FILTER_KEY = "artemis_saved_filter_presets";

describe("S3SearchSection", () => {
  beforeEach(() => {
    localStorage.clear();

    searchS3Mock.mockReset();
    searchS3Mock.mockResolvedValue([]);

    searchS3FoldersMock.mockReset();
    searchS3FoldersMock.mockResolvedValue([
      {
        path: "missions/mars",
        name: "mars",
        depth: 1,
        matched_count: 3,
      },
    ]);

    searchS3FolderChildrenMock.mockReset();
    searchS3FolderChildrenMock.mockResolvedValue({
      path: "missions/mars",
      breadcrumbs: [{ name: "missions", path: "missions" }],
      children: [],
      files: [],
    });

    editObjectTagsMock.mockReset();
    editObjectTagsMock.mockResolvedValue(undefined);

    getRefreshStatusMock.mockReset();
    getRefreshStatusMock.mockResolvedValue({
      status: "idle",
      processed: 0,
      total: 0,
      percent: 0,
    });
  });

  it("test_set_view_mode_resets_folder_state_and_error", async () => {
    const user = userEvent.setup();
    render(S3SearchSection);

    await user.click(screen.getByRole("button", { name: "Folder" }));
    await user.click(screen.getByRole("button", { name: /run search/i }));

    expect(await screen.findByRole("button", { name: /missions\/mars/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "File" }));

    searchS3Mock.mockRejectedValueOnce(new Error("forced search failure"));
    await user.click(screen.getByRole("button", { name: /run search/i }));
    expect(await screen.findByText("forced search failure")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Folder" }));

    expect(screen.queryByText("forced search failure")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /missions\/mars/i })).not.toBeInTheDocument();
    expect(
      screen.getByText("No results yet.", { exact: false }),
    ).toBeInTheDocument();
  });

  it("test_handle_sort_toggles_direction_and_reissues_search", async () => {
    const user = userEvent.setup();

    searchS3Mock.mockResolvedValue([
      {
        key: "mars/file-a.txt",
        size: 10,
        lastModified: "2025-01-01T00:00:00Z",
        storageClass: "STANDARD",
        tags: [],
      },
    ]);

    render(S3SearchSection);

    await user.click(screen.getByRole("button", { name: /run search/i }));
    await waitFor(() => expect(searchS3Mock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByTitle("Sort by Biggest/Smallest"));
    await waitFor(() => expect(searchS3Mock).toHaveBeenCalledTimes(2));

    expect(searchS3Mock.mock.calls[1][0]).toMatchObject({
      sortBy: "Size",
      sortDirection: "desc",
    });

    await user.click(screen.getByTitle("Sort by Biggest/Smallest"));
    await waitFor(() => expect(searchS3Mock).toHaveBeenCalledTimes(3));

    expect(searchS3Mock.mock.calls[2][0]).toMatchObject({
      sortBy: "Size",
      sortDirection: "asc",
    });
  });

  it("test_save_query_deduplicates_and_trims_to_max_queries", async () => {
    const user = userEvent.setup();
    const existingQueries = [
      "zeta",
      "epsilon",
      "delta",
      "gamma",
      "beta",
      "alpha",
      "q1",
      "q2",
      "q3",
      "q4",
    ];
    localStorage.setItem(QUERY_KEY, JSON.stringify(existingQueries));

    render(S3SearchSection);

    const searchInput = screen.getByPlaceholderText("Search ArtemiS3...");
    await user.clear(searchInput);
    await user.type(searchInput, "alpha");
    await user.click(screen.getByRole("button", { name: /run search/i }));

    await waitFor(() => expect(searchS3Mock).toHaveBeenCalled());

    const savedQueries = JSON.parse(localStorage.getItem(QUERY_KEY) ?? "[]");
    expect(savedQueries).toHaveLength(10);
    expect(savedQueries[0]).toBe("alpha");
    expect(savedQueries.filter((query: string) => query === "alpha")).toHaveLength(1);
  });

  it("test_local_storage_malformed_data_does_not_break_initialization", () => {
    localStorage.setItem(QUERY_KEY, "{bad-json");
    localStorage.setItem(FILTER_KEY, "not-json");

    render(S3SearchSection);

    expect(screen.getByRole("button", { name: /run search/i })).toBeInTheDocument();
  });

  it("test_delete_query_updates_dropdown_and_local_storage", async () => {
    const user = userEvent.setup();
    localStorage.setItem(QUERY_KEY, JSON.stringify(["mars", "venus"]));

    render(S3SearchSection);

    const searchInput = screen.getByPlaceholderText("Search ArtemiS3...");
    await user.click(searchInput);
    await user.click(screen.getAllByRole("button", { name: "x" })[0]);

    await waitFor(() => {
      const savedQueries = JSON.parse(localStorage.getItem(QUERY_KEY) ?? "[]");
      expect(savedQueries).toEqual(["venus"]);
    });
  });
});
