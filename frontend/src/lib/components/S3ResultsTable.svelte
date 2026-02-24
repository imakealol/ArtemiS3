<script lang="ts">
  import { type S3ObjectModel } from "../schemas/s3";
  import {
    ChevronFirst,
    ChevronLast,
    ChevronLeft,
    ChevronRight,
    Download,
    FileSearchCorner,
    Pencil,
  } from "@lucide/svelte";
  import EditTagsModal from "./EditTagsModal.svelte";

  export let s3Uri: string = "";
  export let items: S3ObjectModel[] = [];
  export let searchedYet: boolean = false;
  export let onDownload: (key: string, bucket?: string) => void;
  export let onSort: (column: "Key" | "Size" | "LastModified") => void;
  export let editTags: (key: string, tags: string[]) => Promise<void>;
  export let sortBy: "Key" | "Size" | "LastModified" | undefined;
  export let sortDirection: "asc" | "desc";

  const PREVIEWABLE_EXTENSIONS = [
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".mp4",
    ".mp3",
  ];
  const PAGE_SIZE: number = 10;

  let previewKey: string | null = null;
  let previewUrl: string | null = null;

  let page = 0;
  $: maxPage = Math.max(Math.ceil(items.length / PAGE_SIZE) - 1, 0);
  $: if (maxPage) checkMaxPage();

  function checkMaxPage() {
    if (page > maxPage) {
      page = maxPage;
    }
  }

  let editing: string | null = null;

  function setEditing(key: string | null) {
    editing = key;
  }

  async function handlePreview(key: string) {
    // Extract ONLY the bucket name (in case s3Uri is s3://my-bucket/folder/)
    const bucketName = s3Uri.replace(/^s3:\/\//, "").split("/")[0];

    try {
      const response = await fetch(
        `/api/s3/preview?bucket=${encodeURIComponent(bucketName)}&key=${encodeURIComponent(key)}`,
      );

      if (!response.ok) {
        console.error("Preview failed", response.statusText);
        previewUrl = null;
        previewKey = null;
        return;
      }

      const data = await response.json();
      previewUrl = data.preview_url;
      previewKey = key;
    } catch (err) {
      console.error("Preview failed", err);
      previewUrl = null;
      previewKey = null;
    }
  }

  function canPreview(key: string): boolean {
    const lowerKey = key.toLowerCase();
    return PREVIEWABLE_EXTENSIONS.some((ext) => lowerKey.endsWith(ext));
  }

  function formatDate(date: string): string {
    return new Date(date).toLocaleString();
  }
</script>

{#if !searchedYet}
  <!-- Before search has been ran -->
  <p class="mt-3 text-gray-600 text-sm">
    No results yet. Enter a valid S3 URI and run a search.
  </p>
{:else if searchedYet && items.length === 0}
  <!-- Search has been ran but there are no results -->
  <p class="mt-3 text-gray-600 text-sm">
    No results found. Try a different query.
  </p>
{:else}
  <div class="min-h-[510px] flex flex-col justify-between">
    <table
      class="grid-table mt-4 w-full border-collapse text-sm"
      style="grid-template-columns: auto max-content max-content max-content max-content 40px 40px 40px;"
    >
      <thead>
        <tr class="border-b bg-white">
          <th
            title="Sort Alphabetically"
            class="text-left p-2 cursor-pointer w-auto"
            on:click={() => onSort("Key")}
          >
            {sortBy === "Key"
              ? sortDirection === "asc"
                ? "Key ▲"
                : "Key ▼"
              : "Key —"}
          </th>
          <th
            title="Sort by Biggest/Smallest"
            class="text-left p-2 cursor-pointer w-32 whitespace-nowrap"
            on:click={() => onSort("Size")}
          >
            {sortBy === "Size"
              ? sortDirection === "asc"
                ? "Size ▲"
                : "Size ▼"
              : "Size —"}
          </th>
          <th
            title="Sort by Most Recent/Least Recent"
            class="text-left p-2 cursor-pointer w-56 whitespace-nowrap"
            on:click={() => onSort("LastModified")}
          >
            {sortBy === "LastModified"
              ? sortDirection === "asc"
                ? "Last modified  ▲"
                : "Last modified  ▼"
              : "Last modified —"}
          </th>

          <th class="text-left p-2 min-w-[102px]">Storage class</th>
          <th class="text-left p-2">Tags</th>
          <th class="text-center p-2"></th>
          <th class="text-center p-2"></th>
          <th class="text-center p-2"></th>
        </tr>
      </thead>
      <tbody>
        {#each items.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE) as obj}
          <tr class="border-b odd:bg-gray-100">
            <td class="p-2 font-mono text-xs break-all">{obj.key}</td>

            <td class="p-2 whitespace-nowrap">
              {#if obj.size < 1024}
                {obj.size} Bytes
              {:else if obj.size < 1048576}
                {(obj.size / 1024).toFixed(2)} KB
              {:else if obj.size < 1073741824}
                {(obj.size / 1024 ** 2).toFixed(2)} MB
              {:else if obj.size < 1099511627776}
                {(obj.size / 1024 ** 3).toFixed(2)} GB
              {:else}
                {(obj.size / 1024 ** 4).toFixed(2)} TB
              {/if}
            </td>

            <td class="p-2"
              >{obj.lastModified ? formatDate(obj.lastModified) : "unknown"}</td
            >
            <td class="p-2">{obj.storageClass ?? "STANDARD"}</td>
            <td class="p-2 text-wrap max-w-60"
              >{obj.tags && obj.tags.length > 0
                ? obj.tags.join(", ")
                : "No Tags"}</td
            >
            <td class="text-center">
              <button
                on:click={() => onDownload(obj.key)}
                title="Download"
                class="icon-button"
              >
                <Download size={24} />
              </button>
            </td>

            <td class="text-center">
              {#if canPreview(obj.key)}
                <button
                  on:click={() => handlePreview(obj.key)}
                  class="icon-button"
                  title="Preview Document"
                >
                  <FileSearchCorner size={24} />
                </button>
              {:else}
                <button
                  disabled
                  class="icon-button"
                  title="Cannot preview this file type"
                >
                  <FileSearchCorner size={24} />
                </button>
              {/if}
            </td>

            <td class="text-center">
              <button
                class="icon-button"
                title="Edit Tags"
                on:click={() => setEditing(obj.key)}
              >
                <Pencil size={24} />
              </button>
            </td>
          </tr>

          {#if previewUrl && previewKey === obj.key}
            <tr>
              <td
                colspan="6"
                class="p-4 bg-gray-50 border-x border-b shadow-inner"
              >
                <div class="flex flex-col items-center justify-center w-full">
                  {#if obj.key.endsWith(".pdf")}
                    <iframe
                      src={previewUrl}
                      title="PDF Preview"
                      class="w-full max-w-4xl h-[600px] border shadow-md bg-white"
                    ></iframe>
                  {:else if obj.key.endsWith(".mp4")}
                    <div
                      class="bg-black p-1 border shadow-lg rounded-sm w-full max-w-4xl"
                    >
                      <video
                        controls
                        class="w-full max-h-[600px] block mx-auto"
                      >
                        <source src={previewUrl} type="video/mp4" />
                        Your browser does not support the video tag.
                      </video>
                    </div>
                  {:else if obj.key.endsWith(".mp3")}
                    <div
                      class="bg-white p-6 border shadow-lg rounded-md w-full max-w-xl"
                    >
                      <p class="text-xs text-gray-500 mb-2 font-mono">
                        Audio Preview: {obj.key.split("/").pop()}
                      </p>
                      <audio controls src={previewUrl} class="w-full">
                        Your browser does not support the audio element.
                      </audio>
                    </div>
                  {:else if obj.size > 52428800}
                    <div
                      class="flex flex-col items-center p-8 border-2 border-dashed border-gray-300 rounded-lg bg-white shadow-sm text-center max-w-md"
                    >
                      <p class="text-amber-600 font-bold text-lg mb-2">
                        Massive File Notice
                      </p>
                      <p class="text-gray-600 mb-6">
                        This image is <strong
                          >{(obj.size / (1024 * 1024)).toFixed(1)} MB</strong
                        >. To save memory, please open it in a new tab.
                      </p>
                      <a
                        href={previewUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 transition-colors"
                      >
                        Open Full Resolution ↗
                      </a>
                    </div>
                  {:else}
                    <div class="bg-white p-2 border shadow-lg rounded-sm">
                      <img
                        src={previewUrl}
                        alt="Preview"
                        class="max-w-full max-h-[600px] object-contain block mx-auto"
                      />
                    </div>
                  {/if}

                  <button
                    on:click={() => {
                      previewUrl = null;
                      previewKey = null;
                    }}
                    class="mt-4 text-xs text-gray-400 hover:text-red-500 uppercase tracking-widest font-bold cursor-pointer"
                  >
                    [ Close Preview ]
                  </button>
                </div>
              </td>
            </tr>
          {/if}
        {/each}
      </tbody>
    </table>
    <div class="pt-4 pb-2 flex justify-between items-end w-full">
      <span>
        Showing <b>{page * PAGE_SIZE + 1}</b> to
        <b>{Math.min(page * PAGE_SIZE + PAGE_SIZE, items.length)} </b>
        of <b>{items.length}</b> results
      </span>
      <div class="flex">
        <button
          class="page-button border-l rounded-l-xl cursor-pointer disabled:cursor-not-allowed"
          title="Go to the first page"
          disabled={page <= 0}
          on:click={() => (page = 0)}
        >
          <ChevronFirst />
        </button>
        <button
          class="page-button border-l cursor-pointer disabled:cursor-not-allowed"
          title="Go to the previous page"
          disabled={page <= 0}
          on:click={() => page--}
        >
          <ChevronLeft />
        </button>
        <button
          class="page-button border-l cursor-pointer disabled:cursor-not-allowed"
          title="Go to the next page"
          disabled={page >= maxPage}
          on:click={() => page++}
        >
          <ChevronRight />
        </button>
        <button
          class="page-button border-x rounded-r-xl cursor-pointer disabled:cursor-not-allowed"
          title="Go to the last page"
          disabled={page >= maxPage}
          on:click={() => (page = maxPage)}
        >
          <ChevronLast />
        </button>
      </div>
    </div>
  </div>
  <EditTagsModal
    {editing}
    {setEditing}
    localTags={[...(items.find((obj) => obj.key === editing)?.tags ?? [])]}
    submitTags={async (key, tags) => {
      await editTags(key, tags);
      items = items.map((obj) => {
        if (obj.key === key) obj.tags = tags;
        return obj;
      });
      setEditing(null);
    }}
  />
{/if}
