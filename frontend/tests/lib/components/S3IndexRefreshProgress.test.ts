import { render, screen, waitFor } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import S3IndexRefreshProgress from "../../../src/lib/components/S3IndexRefreshProgress.svelte";

const { getRefreshStatusMock } = vi.hoisted(() => ({
  getRefreshStatusMock: vi.fn(),
}));

vi.mock("../../../src/lib/api/s3", () => ({
  getRefreshStatus: getRefreshStatusMock,
}));

describe("S3IndexRefreshProgress", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    getRefreshStatusMock.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("test_start_polling_when_valid_s3_uri_is_provided", async () => {
    getRefreshStatusMock.mockResolvedValue({
      status: "running",
      processed: 8,
      total: 20,
      percent: 40,
    });

    render(S3IndexRefreshProgress, { s3Uri: "s3://bucket/path" });

    await waitFor(() => {
      expect(getRefreshStatusMock).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByText("Refreshing index: 8/20 (40%)")).toBeInTheDocument();

    await vi.advanceTimersByTimeAsync(15000);
    await waitFor(() => {
      expect(getRefreshStatusMock).toHaveBeenCalledTimes(2);
    });
  });

  it("test_stop_polling_when_status_is_done_or_error", async () => {
    getRefreshStatusMock.mockResolvedValue({
      status: "done",
      processed: 20,
      total: 20,
      percent: 100,
    });

    render(S3IndexRefreshProgress, { s3Uri: "s3://bucket/path" });

    await waitFor(() => {
      expect(getRefreshStatusMock).toHaveBeenCalledTimes(1);
    });

    await vi.advanceTimersByTimeAsync(60000);
    expect(getRefreshStatusMock).toHaveBeenCalledTimes(1);
  });

  it("test_reset_to_idle_when_uri_becomes_invalid", async () => {
    getRefreshStatusMock.mockResolvedValue({
      status: "listing",
      processed: 0,
      total: 0,
      percent: 0,
      listed: 99,
    });

    const view = render(S3IndexRefreshProgress, { s3Uri: "s3://bucket/path" });

    await waitFor(() => {
      expect(
        screen.getByText("Index status: scanning objects", { exact: false }),
      ).toBeInTheDocument();
    });

    await view.rerender({ s3Uri: "not-an-s3-uri" });

    expect(
      screen.queryByText("Index status: scanning objects", { exact: false }),
    ).not.toBeInTheDocument();

    await vi.advanceTimersByTimeAsync(30000);
    expect(getRefreshStatusMock).toHaveBeenCalledTimes(1);
  });
});
