<script lang="ts">
  import { type S3ObjectModel } from "../schemas/s3";
  import {
    ChevronFirst,
    ChevronLast,
    ChevronLeft,
    ChevronRight,
    Download,
  } from "@lucide/svelte";

  export let s3Uri: string = "";
  export let items: S3ObjectModel[] = [];
  export let searchedYet: boolean = false;
  export let onDownload: (key: string, bucket: string) => void;

  const PREVIEWABLE_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".webp"];
  const PAGE_SIZE: number = 10;

  let previewKey: string | null = null;
  let previewUrl: string | null = null;

  let page = 0;
  $: maxPage = Math.ceil(items.length / PAGE_SIZE) - 1;
  $: if (maxPage) checkMaxPage();

  function checkMaxPage() {
    if (page > maxPage) {
      page = maxPage;
    }
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
    <table class="mt-4 w-full border-collapse text-sm">
      <thead>
        <tr class="border-b bg-white">
          <th class="text-left p-2">Key</th>
          <th class="text-left p-2">Size</th>
          <th class="text-left p-2">Last modified</th>
          <th class="text-left p-2 min-w-[102px]">Storage class</th>
          <th class="text-center p-2">Download</th>
          <th class="text-center p-2 min-w-[86px]">Preview</th>
        </tr>
      </thead>
      <tbody>
        {#each items.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE) as obj}
          <tr class="border-b odd:bg-gray-100">
            <td class="p-2 font-mono text-xs break-all">{obj.key}</td>

            <td class="p-2 whitespace-nowrap">
              {#if obj.size < 1048576}
                {(obj.size / 1024).toFixed(2)} KB
              {:else}
                {(obj.size / (1024 * 1024)).toFixed(2)} MB
              {/if}
            </td>

            <td class="p-2">{obj.last_modified ?? "unknown"}</td>
            <td class="p-2">{obj.storage_class ?? "STANDARD"}</td>
            <td class="p-2 text-center">
              <button
                on:click={() => onDownload(obj.key)}
                title="Download"
                class="text-blue-600 hover:text-blue-800 cursor-pointer"
              >
                <Download size={18} />
              </button>
            </td>

            <td class="p-2 text-center">
              {#if canPreview(obj.key)}
                <button
                  on:click={() => handlePreview(obj.key)}
                  class="text-green-600 hover:text-green-800 font-bold"
                >
                  Preview
                </button>
              {:else}
                <button
                  disabled
                  class="text-red-400 cursor-not-allowed opacity-70 italic"
                  title="Cannot preview this file type"
                >
                  No Preview
                </button>
              {/if}
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
                    />
                  {:else if obj.size > 52428800}
                    <div
                      class="flex flex-col items-center p-8 border-2 border-dashed border-gray-300 rounded-lg bg-white shadow-sm text-center max-w-md"
                    >
                      <p class="text-amber-600 font-bold text-lg mb-2">
                        Massive File Notice
                      </p>
                      <p class="text-gray-600 mb-6">
                        This file is <strong
                          >{(obj.size / (1024 * 1024)).toFixed(1)} MB</strong
                        >. Loading it here might crash your browser.
                      </p>
                      <a
                        href={previewUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="bg-blue-600 text-white px-6 py-2 rounded-md"
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
                    class="mt-4 text-xs text-gray-400 hover:text-red-500 uppercase tracking-widest font-bold"
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
          class="page-button border-l rounded-l-xl"
          title="Go to the first page"
          disabled={page <= 0}
          on:click={() => (page = 0)}
        >
          <ChevronFirst />
        </button>
        <button
          class="page-button border-l"
          title="Go to the previous page"
          disabled={page <= 0}
          on:click={() => page--}
        >
          <ChevronLeft />
        </button>
        <button
          class="page-button border-l"
          title="Go to the next page"
          disabled={page >= maxPage}
          on:click={() => page++}
        >
          <ChevronRight />
        </button>
        <button
          class="page-button border-x rounded-r-xl"
          title="Go to the last page"
          disabled={page >= maxPage}
          on:click={() => (page = maxPage)}
        >
          <ChevronLast />
        </button>
      </div>
    </div>
  </div>
{/if}
