<script lang="ts">
  import { Search as SearchIcon } from "@lucide/svelte";
  import {
    searchS3,
    searchS3Folders,
    searchS3FolderChildren,
    editObjectTags,
  } from "../api/s3";
  import {
    type S3ObjectModel,
    type S3SearchRequest,
    type S3FolderModel,
    type S3FolderChildrenResponse,
  } from "../schemas/s3";
  import FilterPanel from "../components/FilterPanel.svelte";
  import S3ResultsTable from "../components/S3ResultsTable.svelte";
  import S3FolderExplorer from "../components/S3FolderExplorer.svelte";
  import S3IndexRefreshProgress from "./S3IndexRefreshProgress.svelte";
  import { onMount, onDestroy, tick } from "svelte";
    import type { AnyARecord } from "node:dns";

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
  let viewMode: "file" | "folder" = "file";

  let folderSuggestions: S3FolderModel[] = [];
  let folderChildren: S3FolderModel[] = [];
  let folderBreadcrumbs: S3FolderChildrenResponse["breadcrumbs"] = [];
  let activeFolderPath = "";
  let folderFiles: S3ObjectModel[] = [];

  let sortBy: "Key" | "Size" | "LastModified" | undefined = undefined;
  let sortDirection: "asc" | "desc" = "asc";

  // ===== Local Storage Keys =====
  const QUERY_KEY = "artemis_recent_queries";
  const FILTER_KEY = "artemis_saved_filter_presets";

  const MAX_QUERIES = 10;

  // ===== Recent Queries =====
  let recentQueries: string[] = [];
  let showQueryDropdown = false;
  let dropdownContainer: HTMLDivElement;
  let filterPanelRef: any;

  // ===== Filter Presets =====
  type FilterPreset = {
    name: string;
    filters: FilterState;
  };

  let savedFilterPresets: FilterPreset[] = [];

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
    resetFolderState();
  }

  function handleCustomS3UriInput(value: string) {
    customS3Uri = value;
    if (selectedS3Bucket === "custom") {
      s3Uri = customS3Uri;
    }
    resetFolderState();
  }

  let hasSearched = false;
  function resetFolderState() {
    folderSuggestions = [];
    folderChildren = [];
    folderBreadcrumbs = [];
    activeFolderPath = "";
    folderFiles = [];
  }

  function setViewMode(mode: string) {
    if (mode !== "file" && mode !== "folder") return;
    if (viewMode === mode) return;
    viewMode = mode;
    hasSearched = false;
    s3Error = null;
    resetFolderState();
  }

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
        sortBy,
        sortDirection,
      };
      hasSearched = true;
      s3Results = await searchS3(request);
      saveQuery(s3Contains);
    } catch (err) {
      s3Error = err instanceof Error ? err.message : "Unknown S3 error";
      s3Results = [];
      console.error("S3 search failed:", err);
    } finally {
      s3Loading = false;
    }
  }

  async function loadFolderChildren(path?: string) {
    const data = await searchS3FolderChildren({
      s3Uri,
      path: path || undefined,
      contains: s3Contains || undefined,
      limit: s3Limit,
      sortBy,
      sortDirection,
    });
    activeFolderPath = data.path;
    folderBreadcrumbs = data.breadcrumbs;
    folderChildren = data.children;
    folderFiles = data.files ?? [];
  }

  async function runFolderSearch() {
    s3Loading = true;
    s3Error = null;

    try {
      hasSearched = true;
      saveQuery(s3Contains);
      folderSuggestions = await searchS3Folders({
        s3Uri,
        contains: s3Contains || undefined,
        limit: s3Limit,
      });

      if (folderSuggestions.length > 0) {
        await loadFolderChildren(folderSuggestions[0].path);
      } else {
        folderChildren = [];
        folderBreadcrumbs = [];
        activeFolderPath = "";
        folderFiles = [];
      }
    } catch (err) {
      s3Error =
        err instanceof Error ? err.message : "Unknown folder search error";
      resetFolderState();
      console.error("S3 folder search failed:", err);
    } finally {
      s3Loading = false;
    }
  }

  async function runSearchByMode() {
    if (viewMode === "folder") {
      await runFolderSearch();
      return;
    }
    await runS3Search();
  }

  async function handleSort(column: "Key" | "Size" | "LastModified") {
    if (!column) return;

    // toggle if same column
    if (sortBy === column) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
    } else {
      sortBy = column;
      // default first click direction for all columns
      sortDirection = "desc";
    }

    // load files for folder path
    if (viewMode === "folder") {
      await loadFolderChildren(activeFolderPath || undefined);
      return;
    }
    await runS3Search();
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
    if (s3Uri && viewMode === "file") {
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

  async function openFolder(path: string) {
    await loadFolderChildren(path);
  }

  async function openBreadcrumb(path: string) {
    await loadFolderChildren(path || undefined);
  }

  async function navigateUp() {
    if (!activeFolderPath) return;
    const segments = activeFolderPath.split("/").filter(Boolean);
    segments.pop();
    const parentPath = segments.join("/");
    await loadFolderChildren(parentPath || undefined);
  }

  async function editTags(key: string, tags: string[]) {
    const bucket = getBucketFromUri(s3Uri);
    await editObjectTags(bucket, key, tags);
  }


  // ===== Recent Searches/Filters Functions =====
  onMount(() => {
    if (typeof window === "undefined") return;

    const storedQueries = localStorage.getItem(QUERY_KEY);
    if (storedQueries) {
      recentQueries = JSON.parse(storedQueries);
    }

    const storedFilters = localStorage.getItem(FILTER_KEY);
    if (storedFilters) {
      savedFilterPresets = JSON.parse(storedFilters);
    }

    document.addEventListener("click", handleClickOutside);
  });

  function saveQuery(query: string) {
    if (!query) return;

    const filtered = recentQueries.filter((q) => q !== query);
    recentQueries = [query, ...filtered].slice(0, MAX_QUERIES);

    localStorage.setItem(QUERY_KEY, JSON.stringify(recentQueries));
  }

  function deleteQuery(queryToDelete: string) {
    recentQueries = recentQueries.filter(q => q !== queryToDelete);
    localStorage.setItem(QUERY_KEY, JSON.stringify(recentQueries));
  }

  function saveCurrentFiltersAsPreset() {
    const current = filterPanelRef.getCurrentFilters();

    const name = prompt("Preset name?");
    if (!name) return;

    // Check for duplicate
    const existingIndex = savedFilterPresets.findIndex(f => f.name === name);

    if (existingIndex !== -1) {
      const overwrite = confirm(
        `A filter named "${name}" already exists. Do you want to overwrite it?`
      );
      if (!overwrite) return; // Cancel saving
      // Overwrite existing filter
      savedFilterPresets[existingIndex] = { name, filters: current };
    } else {
      // Add new filter
      savedFilterPresets = [...savedFilterPresets, { name, filters: current }];
    }

    localStorage.setItem(
      FILTER_KEY,
      JSON.stringify(savedFilterPresets)
    );
  }

  async function applyFilterPreset(preset: FilterPreset) {
    s3Filters = preset.filters;

    // wait a tick so FilterPanel updates
    await tick();

    if (viewMode === "file") {
      await runS3Search();
    }
  }

  function handleClickOutside(event: MouseEvent) {
    if (!dropdownContainer) return;

    if (!dropdownContainer.contains(event.target as Node)) {
      showQueryDropdown = false;
    }
  }

  function deleteFilterPreset(name: string) {
    savedFilterPresets = savedFilterPresets.filter(f => f.name !== name);
    localStorage.setItem(FILTER_KEY, JSON.stringify(savedFilterPresets));
  }

  onDestroy(() => {
    document.removeEventListener("click", handleClickOutside);
  });
</script>

<section class={`border rounded p-4 bg-white ${className}`}>
  <h2 class="text-xl font-semibold mb-3">Enter your search:</h2>

  <form
    class="flex flex-wrap gap-3 items-end"
    on:submit|preventDefault={runSearchByMode}
  >
    <div class="flex flex-col">
      <span class="text-sm font-medium mb-1">Mode</span>
      <div class="inline-flex border rounded overflow-hidden">
        <button
          type="button"
          class={`px-3 py-2 text-sm cursor-pointer ${
            viewMode === "file"
              ? "bg-blue-600 text-white"
              : "bg-white text-gray-700"
          }`}
          on:click={() => setViewMode("file")}
        >
          File
        </button>
        <button
          type="button"
          class={`px-3 py-2 text-sm border-l cursor-pointer ${
            viewMode === "folder"
              ? "bg-blue-600 text-white"
              : "bg-white text-gray-700"
          }`}
          on:click={() => setViewMode("folder")}
        >
          Folder
        </button>
      </div>
    </div>

    {#if viewMode === "file"}
      <FilterPanel
        bind:this={filterPanelRef}
        initialFilters={s3Filters}
        onApply={handleFilterApply}
        savedFilters={savedFilterPresets}
        onSave={saveCurrentFiltersAsPreset}
        onDelete={deleteFilterPreset}
      />
    {/if}

    

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

    <div class="flex flex-col relative" bind:this={dropdownContainer}>
      <label for="s3Contains" class="text-sm font-medium mb-1">
        Contains
      </label>

      <input
        id="s3Contains"
        type="text"
        bind:value={s3Contains}
        placeholder="optional substring filter"
        class="border rounded p-2 w-48"
        autocomplete="off"
        on:focus={() => (showQueryDropdown = true)}
        on:blur={() => (showQueryDropdown = true)}
      />

      {#if showQueryDropdown && recentQueries.length > 0}
        <div class="absolute top-full mt-1 w-48 bg-white border rounded shadow z-10 max-h-48 overflow-y-auto">
          {#each recentQueries.filter(q =>
            q.toLowerCase().includes(s3Contains.toLowerCase())
          ) as query}

            <div class="flex items-center justify-between hover:bg-gray-100">
              
              <!-- Clickable search option -->
              <button
                type="button"
                class="w-full text-left px-2 py-1 text-sm"
                on:click={async () => {
                  s3Contains = query;
                  await runSearchByMode();
                  showQueryDropdown = false;
                }}
              >
                {query}
              </button>

              <!-- Delete button -->
              <button
                type="button"
                class="px-2 text-xs text-gray-400 hover:text-red-500"
                on:click={() => deleteQuery(query)}
              >
                ✕
              </button>

            </div>

          {/each}
        </div>
      {/if}
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
      class="flex items-center gap-2 bg-blue-600 text-white px-3 py-2 rounded cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
      disabled={s3Loading}
    >
      <SearchIcon class="w-4 h-4" />
      {#if s3Loading}
        Searching
      {:else}
        {viewMode === "folder" ? "Run Folder Search" : "Run S3 search"}
      {/if}
    </button>
  </form>

  {#if s3Error}
    <p class="mt-3 text-red-600">{s3Error}</p>
  {/if}

  {#if viewMode === "file"}
    <S3ResultsTable
      {s3Uri}
      items={s3Results}
      searchedYet={hasSearched}
      onDownload={handleDownload}
      onSort={handleSort}
      {sortBy}
      {sortDirection}
      {editTags}
    />
  {:else}
    <div class="space-y-4">
      <S3FolderExplorer
        searchedYet={hasSearched}
        loading={s3Loading}
        suggestions={folderSuggestions}
        children={folderChildren}
        files={folderFiles}
        breadcrumbs={folderBreadcrumbs}
        activePath={activeFolderPath}
        {s3Uri}
        {sortBy}
        {sortDirection}
        onOpenFolder={openFolder}
        onOpenBreadcrumb={openBreadcrumb}
        onNavigateUp={navigateUp}
        onSort={handleSort}
        onDownload={handleDownload}
      />
    </div>
  {/if}
</section>
