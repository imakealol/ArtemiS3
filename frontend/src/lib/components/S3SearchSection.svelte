<script lang="ts">
  import { Search as SearchIcon } from "@lucide/svelte";
  import { searchS3 } from "../api/s3";
  import { type S3ObjectModel, type S3SearchRequest } from "../schemas/s3";
  import FilterPanel from "../components/FilterPanel.svelte";
  import S3ResultsTable from "../components/S3ResultsTable.svelte";
  import S3IndexRefreshProgress from "./S3IndexRefreshProgress.svelte";

  export let className = "";

  // expand as more buckets are available (maybe we can make this dynamic?)
  const s3UriOptions = [
    "s3://asc-pds-services",
    "s3://asc-pds-services/pigpen",
    "s3://asc-astropedia",
    "s3://asc-astropedia/Mars",
    "custom",
  ];

  let selectedS3Bucket = s3UriOptions[0];
  let customS3Uri = "";
  let s3Uri = selectedS3Bucket;

  let s3Contains = "";
  let s3Limit = 500;

  let s3Loading = false;
  let s3Error: string | null = null;
  let s3Results: S3ObjectModel[] = [];

  let sort_by: "Key" | "Size" | "LastModified" | undefined = undefined;
  let sort_direction: "asc" | "desc" = "asc";

  type FilterState = {
    suffixes?: string[];
    minSize?: number;
    maxSize?: number;
    storageClasses?: string[];
    modifiedAfter?: string;
    modifiedBefore?: string;
  };
  let s3Filters: FilterState = {};

  type FilterPanelPayload = {
    selectedTypes: string[]; // file types
    minSize?: number;
    maxSize?: number;
    storageClasses?: string[];
    date?: string; // YYYY-MM-DD
    condition?: "after" | "before" | "";
  };

  function handleS3OptionChange(value: string) {
    if (value === "custom") {
      s3Uri = customS3Uri;
    } else {
      s3Uri = value;
    }
  }

  function handleCustomS3UriInput(value: string) {
    customS3Uri = value;
    if (selectedS3Bucket === "custom") {
      s3Uri = customS3Uri;
    }
  }

  let hasSearched = false;
  async function runS3Search() {
    s3Loading = true;
    s3Error = null;

    try {
      const request: S3SearchRequest = {
        s3Uri: s3Uri,
        contains: s3Contains || undefined,
        limit: s3Limit,
        suffixes: s3Filters.suffixes,
        minSize: s3Filters.minSize,
        maxSize: s3Filters.maxSize,
        storageClasses: s3Filters.storageClasses,
        modifiedAfter: s3Filters.modifiedAfter,
        modifiedBefore: s3Filters.modifiedBefore,
        sort_by,
        sort_direction,
      };

      hasSearched = true;
      s3Results = await searchS3(request);
    } catch (err) {
      s3Error = err instanceof Error ? err.message : "Unknown S3 error";
      s3Results = [];
      console.error("S3 search failed:", err);
    } finally {
      s3Loading = false;
    }
  }

  function handleSort(column: "Key" | "Size" | "LastModified") {
    if (!column) return;

    // toggle if same column
    if (sort_by === column) {
      sort_direction = sort_direction === "asc" ? "desc" : "asc";
    } else {
      sort_by = column;
      // default first click direction for all columns
      sort_direction = "desc";
    }

    runS3Search();
  }

  // calls on apply from FilterPanel
  async function handleFilterApply(payload: FilterPanelPayload) {
    const next: FilterState = {};

    if (payload.selectedTypes && payload.selectedTypes.length > 0) {
      next.suffixes = payload.selectedTypes;
    }

    if (typeof payload.minSize === "number") {
      next.minSize = payload.minSize;
    }

    if (typeof payload.maxSize === "number") {
      next.maxSize = payload.maxSize;
    }

    if (payload.storageClasses && payload.storageClasses.length > 0) {
      next.storageClasses = payload.storageClasses;
    }

    if (payload.date && payload.condition == "after") {
      next.modifiedAfter = payload.date;
    } else if (payload.date && payload.condition == "before") {
      next.modifiedBefore = payload.date;
    }

    s3Filters = next;

    // rerun search when filters are applied
    if (s3Uri) {
      await runS3Search();
    }
  }

  function getBucketFromUri(uri: string): string {
    if (!uri.startsWith("s3://")) return "";
    return uri.slice("s3://".length).split("/")[0];
  }

  async function handleDownload(key: string) {
    const bucket = getBucketFromUri(s3Uri);
    const fileUri = `s3://${bucket}/${key}`;
    const url = `/api/s3/download?s3_uri=${encodeURIComponent(fileUri)}`;

    // trigger browser download
    window.location.href = url;
  }
</script>

<section class={`border rounded p-4 bg-white ${className}`}>
  <h2 class="text-xl font-semibold mb-3">Enter your search:</h2>

  <form
    class="flex flex-wrap gap-3 items-end"
    on:submit|preventDefault={runS3Search}
  >
    <FilterPanel onApply={handleFilterApply} />
    <div class="flex flex-col">
      <label for="s3Uri" class="text-sm font-medium mb-1">S3 URI</label>
      <select
        id="s3Uri"
        bind:value={selectedS3Bucket}
        placeholder="s3://bucket/prefix"
        class="border rounded p-2 w-72"
        on:change={(e) => handleS3OptionChange(e.currentTarget.value)}
        required
      >
        {#each s3UriOptions as option}
          <option value={option}>
            {option === "custom" ? "Custom..." : option}
          </option>
        {/each}
      </select>

      {#if selectedS3Bucket === "custom"}
        <input
          type="text"
          placeholder="s3://bucket/prefix"
          class="border rounded p-2 w-72 mt-2"
          value={customS3Uri}
          on:input={(e) => handleCustomS3UriInput(e.currentTarget.value)}
          required
        />
      {/if}
    </div>

    <S3IndexRefreshProgress {s3Uri} />

    <div class="flex flex-col">
      <label for="s3Contains" class="text-sm font-medium mb-1">
        Contains
      </label>
      <input
        id="s3Contains"
        type="text"
        bind:value={s3Contains}
        placeholder="optional substring filter"
        class="border rounded p-2 w-48"
      />
    </div>

    <div class="flex flex-col">
      <label for="s3Limit" class="text-sm font-medium mb-1">Limit</label>
      <input
        id="s3Limit"
        type="number"
        min="1"
        max="1000"
        bind:value={s3Limit}
        class="border rounded p-2 w-24"
      />
    </div>

    <button
      type="submit"
      class="flex items-center gap-2 bg-blue-600 text-white px-3 py-2 rounded disabled:opacity-60"
      disabled={s3Loading}
    >
      <SearchIcon class="w-4 h-4" />
      {#if s3Loading}
        Searching
      {:else}
        Run S3 search
      {/if}
    </button>
  </form>

  {#if s3Error}
    <p class="mt-3 text-red-600">{s3Error}</p>
  {/if}

  <S3ResultsTable
    {s3Uri}
    items={s3Results}
    searchedYet={hasSearched}
    onDownload={handleDownload}
    onSort={handleSort}
    {sort_by}
    {sort_direction}
  />
</section>
