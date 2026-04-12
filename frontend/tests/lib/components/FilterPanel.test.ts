import { render, screen, waitFor } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import FilterPanel from "../../../src/lib/components/FilterPanel.svelte";

describe("FilterPanel", () => {
  it("test_send_filter_converts_units_to_bytes_before_on_apply", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();

    render(FilterPanel, {
      onApply,
      initialFilters: null,
      savedFilters: [],
    });

    await user.click(screen.getByRole("button", { name: /filter/i }));

    await user.type(screen.getByPlaceholderText("0"), "1.5");
    await user.selectOptions(screen.getAllByRole("combobox")[0], "1048576");

    await waitFor(() => {
      expect(onApply).toHaveBeenCalled();
    });

    const lastPayload = onApply.mock.calls.at(-1)?.[0];
    expect(lastPayload.minSize).toBe(1572864);
  });

  it("test_reset_filters_emits_empty_payload", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();

    render(FilterPanel, {
      onApply,
      initialFilters: null,
      savedFilters: [],
    });

    await user.click(screen.getByRole("button", { name: /filter/i }));
    await user.click(screen.getByRole("checkbox", { name: "pdf" }));
    await user.type(screen.getByPlaceholderText("0"), "3");

    await user.click(screen.getByRole("button", { name: "Clear all filters" }));

    await waitFor(() => {
      expect(onApply).toHaveBeenCalled();
    });

    expect(onApply).toHaveBeenLastCalledWith({
      selectedTypes: [],
      minSize: undefined,
      maxSize: undefined,
      storageClasses: undefined,
      date: undefined,
      condition: "",
    });
  });

  it("test_add_custom_type_ignores_empty_and_duplicate_values", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();

    render(FilterPanel, {
      onApply,
      initialFilters: null,
      savedFilters: [],
    });

    await user.click(screen.getByRole("button", { name: /filter/i }));

    const customTypeInput = screen.getByPlaceholderText("+ add type (csv, tif, lbl)");
    await user.type(customTypeInput, "csv{enter}");
    await user.type(customTypeInput, ".csv{enter}");
    await user.type(customTypeInput, "   {enter}");

    await waitFor(() => {
      expect(onApply).toHaveBeenCalled();
    });

    expect(screen.getAllByText("csv")).toHaveLength(1);
    const lastPayload = onApply.mock.calls.at(-1)?.[0];
    expect(lastPayload.selectedTypes).toEqual(["csv"]);
  });

  it("test_apply_saved_filter_populates_fields_and_emits_payload", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();

    render(FilterPanel, {
      onApply,
      initialFilters: null,
      savedFilters: [
        {
          name: "Geo PDFs",
          filters: {
            suffixes: ["pdf"],
            minSize: 1024,
            maxSize: 2048,
            storageClasses: ["STANDARD"],
            modifiedBefore: "2025-01-01",
          },
        },
      ],
    });

    await user.click(screen.getByRole("button", { name: /filter/i }));
    await user.click(screen.getByRole("button", { name: "Saved Filters" }));
    await user.click(screen.getByRole("button", { name: "Geo PDFs" }));

    await waitFor(() => {
      expect(onApply).toHaveBeenCalled();
    });

    expect(onApply).toHaveBeenLastCalledWith({
      selectedTypes: ["pdf"],
      minSize: 1024,
      maxSize: 2048,
      storageClasses: ["STANDARD"],
      date: "2025-01-01",
      condition: "before",
    });

    expect(
      screen.queryByPlaceholderText("Search saved filters..."),
    ).not.toBeInTheDocument();
  });

  it("test_get_current_filters_handles_initial_after_date_and_nan_sizes", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();

    const view = render(FilterPanel, {
      onApply,
      initialFilters: {
        suffixes: ["txt"],
        minSize: Number.NaN,
        maxSize: 2097152,
        storageClasses: ["GLACIER"],
        modifiedAfter: "2026-01-01",
      },
      savedFilters: [],
    });

    await user.click(screen.getByRole("button", { name: /filter/i }));

    const currentFilters = (view.component as { getCurrentFilters: () => unknown }).getCurrentFilters();
    expect(currentFilters).toEqual({
      suffixes: ["txt"],
      maxSize: 2097152,
      storageClasses: ["GLACIER"],
      modifiedAfter: "2026-01-01",
    });
  });
});
