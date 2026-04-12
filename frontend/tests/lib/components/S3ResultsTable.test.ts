import { render, screen, waitFor } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import S3ResultsTable from "../../../src/lib/components/S3ResultsTable.svelte";
import type { S3ObjectModel } from "../../../src/lib/schemas/s3";

function makeItems(total: number): S3ObjectModel[] {
  return Array.from({ length: total }, (_, index) => ({
    key: `folder/file-${index + 1}.txt`,
    size: 1024 + index,
    lastModified: "2025-01-01T00:00:00Z",
    storageClass: "STANDARD",
    tags: [`tag-${index + 1}`],
  }));
}

describe("S3ResultsTable", () => {
  it("test_pagination_controls_enable_and_disable_at_bounds", async () => {
    const user = userEvent.setup();

    render(S3ResultsTable, {
      s3Uri: "s3://bucket",
      items: makeItems(12),
      searchedYet: true,
      onDownload: vi.fn(),
      onSort: vi.fn(),
      editTags: vi.fn().mockResolvedValue(undefined),
      sortBy: undefined,
      sortDirection: "asc",
    });

    const firstPageButton = screen.getByTitle("Go to the first page");
    const previousPageButton = screen.getByTitle("Go to the previous page");
    const nextPageButton = screen.getByTitle("Go to the next page");
    const lastPageButton = screen.getByTitle("Go to the last page");

    expect(firstPageButton).toBeDisabled();
    expect(previousPageButton).toBeDisabled();
    expect(nextPageButton).toBeEnabled();
    expect(lastPageButton).toBeEnabled();
    expect(screen.getByText(/Showing/i)).toHaveTextContent("Showing 1 to 10 of 12 results");

    await user.click(nextPageButton);

    expect(firstPageButton).toBeEnabled();
    expect(previousPageButton).toBeEnabled();
    expect(nextPageButton).toBeDisabled();
    expect(lastPageButton).toBeDisabled();
    expect(screen.getByText(/Showing/i)).toHaveTextContent("Showing 11 to 12 of 12 results");
  });

  it("test_preview_button_disabled_for_non_previewable_extensions", () => {
    render(S3ResultsTable, {
      s3Uri: "s3://bucket",
      items: [
        {
          key: "folder/archive.bin",
          size: 2048,
          lastModified: "2025-01-01T00:00:00Z",
          storageClass: "STANDARD",
          tags: [],
        },
      ],
      searchedYet: true,
      onDownload: vi.fn(),
      onSort: vi.fn(),
      editTags: vi.fn().mockResolvedValue(undefined),
      sortBy: undefined,
      sortDirection: "asc",
    });

    expect(
      screen.getByTitle("Cannot preview this file type"),
    ).toBeDisabled();
  });

  it("test_submit_tags_updates_item_tags_and_closes_modal", async () => {
    const user = userEvent.setup();
    const editTags = vi.fn().mockResolvedValue(undefined);

    render(S3ResultsTable, {
      s3Uri: "s3://bucket",
      items: [
        {
          key: "folder/report.txt",
          size: 1111,
          lastModified: "2025-01-01T00:00:00Z",
          storageClass: "STANDARD",
          tags: ["existing"],
        },
      ],
      searchedYet: true,
      onDownload: vi.fn(),
      onSort: vi.fn(),
      editTags,
      sortBy: undefined,
      sortDirection: "asc",
    });

    await user.click(screen.getByTitle("Edit tags"));

    const tagInput = await screen.findByPlaceholderText("mars-rover-2020");
    await user.type(tagInput, "new-tag{enter}");
    await user.click(screen.getByRole("button", { name: "Save Changes" }));

    await waitFor(() => {
      expect(editTags).toHaveBeenCalledWith("folder/report.txt", [
        "existing",
        "new-tag",
      ]);
    });

    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: "Save Changes" }),
      ).not.toBeInTheDocument();
    });

    expect(screen.getByText("existing, new-tag")).toBeInTheDocument();
  });
});
