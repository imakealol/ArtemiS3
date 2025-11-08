<script lang="ts">
  import {Search as SearchIcon, ChevronDown } from "@lucide/svelte"

  let name = "ArtemiS3";
  async function ping() {
    const res = await fetch("/api/test?name=Svelte");
    const data = await res.json();
    alert(JSON.stringify(data))
  }

import { onMount, onDestroy } from "svelte";

let showSort = false;

// sort state
let sortField: "name" | "date" | "type" | "size" | null = null;
let sortDirection: "none" | "desc" | "asc" = "none";

// elements for click-outside
let sortButtonEl: HTMLElement | null = null;
let sortPanelEl: HTMLElement | null = null;

function cycleSortFor(field: "name" | "date" | "type" | "size") {
  if (sortField !== field) {
    // new field chosen => start with descending
    sortField = field;
    sortDirection = "desc";
  } else {
    // same field clicked => cycle: desc -> asc -> none
    if (sortDirection === "none") {
      sortDirection = "desc";
    } else if (sortDirection === "desc") {
      sortDirection = "asc";
    } else {
      // was asc -> clear
      sortField = null;
      sortDirection = "none";
    }
  }

  // 
  //    IMPLIMENT LATER!!!!
  //    Sorting logic
  //
  console.log("Sort state:", { sortField, sortDirection });
}

// click-outside to close panel
function handleDocClick(e: MouseEvent) {
  const t = e.target as Node;
  if (!showSort) return;
  if (sortPanelEl && sortPanelEl.contains(t)) return;
  if (sortButtonEl && sortButtonEl.contains(t)) return;
  showSort = false;
}

onMount(() => document.addEventListener("click", handleDocClick));
onDestroy(() => document.removeEventListener("click", handleDocClick));

// small inline SVG helpers returned as strings so we can render via {@html ...}
function DownIcon() {
  return `
    <svg xmlns="http://www.w3.org/2000/svg"
         class="inline-block w-4 h-4 text-gray-700"
         fill="none"
         viewBox="0 0 24 24"
         stroke="currentColor">
      <path stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M19 9l-7 7-7-7" />
    </svg>`;
}

function UpIcon() {
  return `
    <svg xmlns="http://www.w3.org/2000/svg"
         class="inline-block w-4 h-4 text-gray-700"
         fill="none"
         viewBox="0 0 24 24"
         stroke="currentColor">
      <path stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M5 15l7-7 7 7" />
    </svg>`;
}

</script>

<main>
  <div class="w-screen h-screen p-8">
    <h1>Welcome to {name}</h1>
    <p>Frontend is up. NGINX proxies this page and /api to FastAPI.</p>
    <button on:click={ping} class="button">Test API</button>
    <h2>Search Page Prototype:</h2>
      <div class="aspect-16/9 mt-2 w-6xl border-2">
        <div class="border-b h-1/6 flex flex-col items-center justify-center">
          <h1>ArtemiS3</h1>
        </div>
        <div class="flex flex-col h-5/6 items-center justify-evenly">
          <div class="flex flex-col items-center">
            <div class="text-nowrap w-80 flex">
              <input class="w-full !p-2 !rounded-r-none shadow z-2" placeholder="Search for Files" />
              <span class="border border-l-white border-gray-400 flex items-center justify-center
                           rounded-r-lg aspect-1/1 w-fit h-full hover:outline text-gray-500 hover:border-l-gray-400
                           hover:text-gray-700 active:bg-gray-200 cursor-pointer shadow z-1 hover:z-3">
                <SearchIcon />
              </span>
            </div>
          </div>
          <div class="w-5/6 h-7/10 flex flex-col items-center gap-2">
            <div class="w-full flex justify-end relative">
              <div class="relative">
                <button
                  bind:this={sortButtonEl}
                  on:click={() => (showSort = !showSort)}
                  class="flex items-center gap-2 px-3 py-2 bg-gray-100 border rounded hover:bg-gray-200"
                  type="button"
                  aria-expanded={showSort}
                >
                  <!-- hamburger-style icon -->
                  <div class="space-y-1">
                    <span class="block w-4 h-0.5 bg-gray-700"></span>
                    <span class="block w-4 h-0.5 bg-gray-700"></span>
                    <span class="block w-4 h-0.5 bg-gray-700"></span>
                  </div>
                  <span class="ml-1">Sort</span>
                </button>

                {#if showSort}
                  <div
                    bind:this={sortPanelEl}
                    class="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded shadow-lg z-30 overflow-hidden"
                  >
                    <!-- sort options list -->
                    <div class="flex flex-col">
                      <!-- Name -->
                      <button
                        type="button"
                        on:click={() => cycleSortFor("name")}
                        class="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center justify-between"
                      >
                        <span class="text-sm">Name</span>
                        {#if sortField === 'name'}
                          {@html sortDirection === 'desc' ? DownIcon() : (sortDirection === 'asc' ? UpIcon() : '')}
                        {/if}
                      </button>

                      <!-- Date -->
                      <button
                        type="button"
                        on:click={() => cycleSortFor("date")}
                        class="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center justify-between"
                      >
                        <span class="text-sm">Date</span>
                        {#if sortField === 'date'}
                          {@html sortDirection === 'desc' ? DownIcon() : (sortDirection === 'asc' ? UpIcon() : '')}
                        {/if}
                      </button>

                      <!-- Type -->
                      <button
                        type="button"
                        on:click={() => cycleSortFor("type")}
                        class="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center justify-between"
                      >
                        <span class="text-sm">Type</span>
                        {#if sortField === 'type'}
                          {@html sortDirection === 'desc' ? DownIcon() : (sortDirection === 'asc' ? UpIcon() : '')}
                        {/if}
                      </button>

                      <!-- Size -->
                      <button
                        type="button"
                        on:click={() => cycleSortFor("size")}
                        class="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center justify-between"
                      >
                        <span class="text-sm">Size</span>
                        {#if sortField === 'size'}
                          {@html sortDirection === 'desc' ? DownIcon() : (sortDirection === 'asc' ? UpIcon() : '')}
                        {/if}
                      </button>
                    </div>

                    <!-- footer actions -->
                    <div class="flex justify-between items-center px-2 py-2 border-t bg-gray-50">
                      <button
                        type="button"
                        class="text-xs text-gray-600 hover:underline"
                        on:click={() => { sortField = null; sortDirection = 'none'; }}
                      >
                        Clear
                      </button>
                      <button
                        type="button"
                        class="text-xs px-3 py-1 bg-blue-600 text-white rounded"
                        on:click={() => (showSort = false)}
                      >
                        Done
                      </button>
                    </div>
                  </div>
                {/if}
              </div>
            </div>
            <div class="w-full h-full text-center border">
              results
            </div>
          </div>
        </div>
      </div>
  </div>
</main>
