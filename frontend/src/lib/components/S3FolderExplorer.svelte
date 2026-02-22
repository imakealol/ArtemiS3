<script lang="ts">
  import {
    Download as DownloadIcon,
    Eye as EyeIcon,
    File as FileIcon,
    Folder as FolderIcon,
    FolderOpen as FolderOpenIcon,
  } from "@lucide/svelte";
  import type {
    S3BreadcrumbModel,
    S3FolderModel,
    S3ObjectModel,
  } from "../schemas/s3";

  const PREVIEWABLE_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".webp"];

  export let searchedYet = false;
  export let loading = false;
  export let s3Uri = "";
  export let suggestions: S3FolderModel[] = [];
  export let children: S3FolderModel[] = [];
  export let files: S3ObjectModel[] = [];
  export let breadcrumbs: S3BreadcrumbModel[] = [];
  export let activePath = "";
  export let sortBy: "Key" | "Size" | "LastModified" | undefined = undefined;
  export let sortDirection: "asc" | "desc" = "asc";

  export let onOpenFolder: (path: string) => void = () => {};
  export let onOpenBreadcrumb: (path: string) => void = () => {};
  export let onNavigateUp: () => void = () => {};
  export let onSort: (
    column: "Key" | "Size" | "LastModified",
  ) => void = () => {};
  export let onDownload: (key: string) => void = () => {};

  let previewKey: string | null = null;
  let previewUrl: string | null = null;
  let previewError: string | null = null;
  let previewLoading = false;
  let selectedRow: string | null = null;
  let selectedFolderPath: string | null = null;

  $: if (selectedFolderPath === null && activePath) {
    selectedFolderPath = activePath;
  }
  $: sortedChildren = [...children].sort((a, b) =>
    a.name.localeCompare(b.name),
  );
  $: if (previewKey && !files.some((item) => item.key === previewKey)) {
    clearPreview();
  }

  function clearPreview() {
    previewKey = null;
    previewUrl = null;
    previewError = null;
    previewLoading = false;
  }

  function getBucketFromUri(uri: string): string {
    if (!uri.startsWith("s3://")) return "";
    return uri.slice("s3://".length).split("/")[0];
  }

  function canPreview(key: string): boolean {
    const lowerKey = key.toLowerCase();
    return PREVIEWABLE_EXTENSIONS.some((ext) => lowerKey.endsWith(ext));
  }

  function displayName(key: string): string {
    const segments = key.split("/").filter(Boolean);
    return segments[segments.length - 1] || key;
  }

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024)
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  }

  function selectFolder(path: string) {
    selectedFolderPath = path;
    selectedRow = `folder:${path}`;
  }

  async function openFolder(path: string) {
    clearPreview();
    selectFolder(path);
    await onOpenFolder(path);
  }

  async function openBreadcrumb(path: string) {
    clearPreview();
    selectedRow = null;
    selectedFolderPath = path || null;
    await onOpenBreadcrumb(path);
  }

  async function handlePreview(key: string) {
    if (!canPreview(key)) return;

    if (previewKey === key && previewUrl) {
      clearPreview();
      return;
    }

    previewLoading = true;
    previewError = null;
    previewKey = key;
    previewUrl = null;

    const bucketName = getBucketFromUri(s3Uri);
    if (!bucketName) {
      previewLoading = false;
      previewError = "Invalid S3 URI for preview.";
      return;
    }

    try {
      const response = await fetch(
        `/api/s3/preview?bucket=${encodeURIComponent(bucketName)}&key=${encodeURIComponent(key)}`,
      );
      if (!response.ok) {
        previewError = `Preview failed: ${response.status}`;
        return;
      }
      const data = await response.json();
      previewUrl = data.preview_url ?? null;
      if (!previewUrl) {
        previewError = "Preview URL was not returned by the server.";
      }
    } catch (err) {
      previewError = err instanceof Error ? err.message : "Preview failed.";
    } finally {
      previewLoading = false;
    }
  }
</script>

{#if !searchedYet}
  <p class="mt-3 text-gray-600 text-sm">
    No results yet. Enter a valid S3 URI and run a folder search.
  </p>
{:else if searchedYet && suggestions.length === 0}
  <p class="mt-3 text-gray-600 text-sm">
    No folders found. Try a different query.
  </p>
{:else}
  <div class="mt-4 border border-gray-200 rounded-lg bg-white overflow-hidden">
    <div
      class="px-3 py-2 border-b border-gray-200 bg-gray-50 flex flex-wrap items-center gap-2 justify-between"
    >
      <div class="flex items-center gap-2 min-w-0 flex-wrap">
        <span class="text-sm font-medium text-gray-700">Path</span>
        <button
          type="button"
          class="text-sm text-blue-700 hover:text-blue-800 underline cursor-pointer"
          on:click={() => openBreadcrumb("")}
        >
          root
        </button>
        {#each breadcrumbs as crumb}
          <span class="text-gray-400">/</span>
          <button
            type="button"
            class="text-sm text-blue-700 hover:text-blue-800 underline cursor-pointer"
            on:click={() => openBreadcrumb(crumb.path)}
          >
            {crumb.name}
          </button>
        {/each}
      </div>
      <div class="flex items-center gap-2">
        {#if loading}
          <span class="text-xs text-gray-500">Loading...</span>
        {/if}
        <button
          type="button"
          class="px-2 py-1 text-xs border border-gray-300 rounded bg-white hover:bg-gray-100 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
          on:click={onNavigateUp}
          disabled={!activePath || loading}
        >
          Up
        </button>
      </div>
    </div>

    <div
      class="grid grid-cols-1 lg:grid-cols-[18rem_minmax(0,1fr)] min-h-[430px]"
    >
      <aside
        class="border-b lg:border-b-0 lg:border-r border-gray-200 bg-white p-3"
      >
        <h3 class="text-sm font-semibold text-gray-700 mb-2">
          Relevant folders
        </h3>
        {#if suggestions.length === 0}
          <p class="text-sm text-gray-500">No relevant folders.</p>
        {:else}
          <ul class="space-y-1 max-h-[360px] overflow-auto pr-1">
            {#each suggestions as folder}
              <li>
                <button
                  type="button"
                  class={`w-full text-left text-sm px-2 py-1 rounded border cursor-pointer flex items-center justify-between gap-2 ${
                    selectedFolderPath === folder.path
                      ? "bg-blue-50 border-blue-200 text-blue-900"
                      : "border-transparent hover:bg-gray-50 hover:border-gray-200"
                  }`}
                  on:click={() => openFolder(folder.path)}
                >
                  <span class="truncate font-mono">{folder.path}</span>
                  <span class="text-xs text-gray-500 shrink-0"
                    >{folder.matched_count}</span
                  >
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </aside>

      <div class="p-3 bg-white space-y-3">
        <div class="border border-gray-200 rounded-lg overflow-hidden">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th
                  title="Sort Alphabetically"
                  class="text-left p-2 cursor-pointer"
                  on:click={() => onSort("Key")}
                >
                  {sortBy === "Key"
                    ? sortDirection === "asc"
                      ? "Name \u25B2"
                      : "Name \u25BC"
                    : "Name \u2014"}
                </th>
                <th
                  title="Sort by Biggest/Smallest"
                  class="text-left p-2 cursor-pointer"
                  on:click={() => onSort("Size")}
                >
                  {sortBy === "Size"
                    ? sortDirection === "asc"
                      ? "Size \u25B2"
                      : "Size \u25BC"
                    : "Size \u2014"}
                </th>
                <th
                  title="Sort by Most Recent/Least Recent"
                  class="text-left p-2 cursor-pointer"
                  on:click={() => onSort("LastModified")}
                >
                  {sortBy === "LastModified"
                    ? sortDirection === "asc"
                      ? "Last modified  \u25B2"
                      : "Last modified  \u25BC"
                    : "Last modified \u2014"}
                </th>
                <th class="p-2 text-left">Storage Class</th>
                <th class="p-2 text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {#if sortedChildren.length === 0 && files.length === 0}
                <tr>
                  <td colspan="5" class="p-6 text-center text-sm text-gray-500">
                    This folder is empty.
                  </td>
                </tr>
              {:else}
                {#each sortedChildren as child}
                  <tr class="border-gray-100 hover:bg-gray-50">
                    <td class="p-2">
                      <button
                        type="button"
                        class={`w-full text-left flex items-center gap-2 cursor-pointer rounded px-1 py-1 border ${
                          selectedFolderPath === child.path
                            ? "bg-blue-50 border-blue-200 text-blue-900"
                            : "border-transparent hover:bg-gray-50 hover:border-gray-200"
                        }`}
                        on:click={() => selectFolder(child.path)}
                        on:dblclick={() => openFolder(child.path)}
                        title={child.path}
                      >
                        {#if selectedFolderPath === child.path}
                          <FolderOpenIcon
                            class="w-4 h-4 text-amber-600 shrink-0"
                          />
                        {:else}
                          <FolderIcon class="w-4 h-4 text-amber-500 shrink-0" />
                        {/if}
                        <span class="truncate">{child.name}</span>
                      </button>
                    </td>
                    <td class="p-2 text-gray-500">-</td>
                    <td class="p-2 text-gray-500">-</td>
                    <td class="p-2 text-gray-500">Folder</td>
                    <td class="p-2 text-center">
                      <button
                        type="button"
                        class="text-blue-700 hover:text-blue-800 text-xs cursor-pointer"
                        on:click={() => openFolder(child.path)}
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                {/each}

                {#each files as file}
                  <tr
                    class={`border-b border-gray-100 hover:bg-gray-50 ${
                      selectedRow === `file:${file.key}` ? "bg-blue-50" : ""
                    }`}
                  >
                    <td class="p-2">
                      <button
                        type="button"
                        class="w-full text-left flex items-center gap-2 cursor-pointer"
                        on:click={() => (selectedRow = `file:${file.key}`)}
                        title={file.key}
                      >
                        <FileIcon class="w-4 h-4 text-gray-500 shrink-0" />
                        <span class="truncate">{displayName(file.key)}</span>
                      </button>
                    </td>
                    <td class="p-2 whitespace-nowrap"
                      >{formatSize(file.size)}</td
                    >
                    <td class="p-2">{file.lastModified ?? "Unknown"}</td>
                    <td class="p-2">{file.storageClass ?? "STANDARD"}</td>
                    <td class="p-2">
                      <div class="flex items-center justify-center gap-2">
                        <button
                          type="button"
                          class="text-blue-700 hover:text-blue-800 cursor-pointer"
                          title="Download"
                          on:click={() => onDownload(file.key)}
                        >
                          <DownloadIcon class="w-4 h-4" />
                        </button>
                        <button
                          type="button"
                          class={canPreview(file.key)
                            ? "text-emerald-700 hover:text-emerald-800 cursor-pointer"
                            : "text-gray-300 cursor-not-allowed"}
                          title={canPreview(file.key)
                            ? "Preview"
                            : "Preview unavailable for this file type"}
                          on:click={() => handlePreview(file.key)}
                          disabled={!canPreview(file.key)}
                        >
                          <EyeIcon class="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                  {#if previewKey === file.key}
                    <tr class="border-b border-gray-100 bg-gray-50">
                      <td colspan="5" class="p-3">
                        <div class="flex items-center justify-between gap-2 mb-2">
                          <p class="text-sm font-medium text-gray-700 truncate">
                            Preview {previewKey}
                          </p>
                          <button
                            type="button"
                            class="text-xs text-gray-500 hover:text-red-600 cursor-pointer"
                            on:click={clearPreview}
                          >
                            Close
                          </button>
                        </div>
                        {#if previewLoading}
                          <p class="text-sm text-gray-500">Loading preview...</p>
                        {:else if previewError}
                          <p class="text-sm text-red-600">{previewError}</p>
                        {:else if previewUrl}
                          {#if previewKey?.toLowerCase().endsWith(".pdf")}
                            <iframe
                              src={previewUrl}
                              title="PDF preview"
                              class="w-full h-[560px] border border-gray-200 bg-white"
                            ></iframe>
                          {:else if file.size > 52428800}
                            <div
                              class="p-4 border border-amber-200 rounded bg-amber-50 text-sm text-amber-900"
                            >
                              <p>
                                This file is {formatSize(file.size)}. Open it in a
                                new tab for a safer preview.
                              </p>
                              <a
                                class="mt-2 inline-block text-blue-700 hover:text-blue-800 underline"
                                href={previewUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                Open preview in new tab
                              </a>
                            </div>
                          {:else}
                            <div class="bg-white p-2 border border-gray-200 rounded">
                              <img
                                src={previewUrl}
                                alt="S3 file preview"
                                class="max-w-full max-h-[560px] object-contain mx-auto"
                              />
                            </div>
                          {/if}
                        {/if}
                      </td>
                    </tr>
                  {/if}
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
{/if}

