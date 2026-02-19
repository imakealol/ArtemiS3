<script lang="ts">
  import type { S3BreadcrumbModel, S3FolderModel } from "../schemas/s3";

  export let searchedYet: boolean = false;
  export let loading: boolean = false;
  export let suggestions: S3FolderModel[] = [];
  export let children: S3FolderModel[] = [];
  export let breadcrumbs: S3BreadcrumbModel[] = [];
  export let activePath: string = "";
  export let onOpenFolder: (path: string) => void;
  export let onOpenBreadcrumb: (path: string) => void;
  export let onNavigateUp: () => void;
</script>

{#if searchedYet && suggestions.length === 0}
  <p class="mt-3 text-gray-600 text-sm">
    No folders found. Try a different query.
  </p>
{:else}
  <div class="mt-4 border rounded p-3 bg-gray-50 space-y-3">
    <div class="flex items-center gap-2 flex-wrap">
      <span class="text-sm font-medium">Path:</span>
      <button
        type="button"
        class="text-blue-600 underline text-sm cursor-pointer"
        on:click={() => onOpenBreadcrumb("")}
      >
        root
      </button>
      {#each breadcrumbs as crumb}
        <span class="text-gray-400">/</span>
        <button
          type="button"
          class="text-blue-600 underline text-sm cursor-pointer"
          on:click={() => onOpenBreadcrumb(crumb.path)}
        >
          {crumb.name}
        </button>
      {/each}
      <button
        type="button"
        class="ml-2 px-2 py-1 text-xs border rounded cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
        on:click={onNavigateUp}
        disabled={!activePath || loading}
      >
        Up
      </button>
    </div>

    <div class="grid gap-3 md:grid-cols-2">
      <div>
        <h3 class="text-sm font-semibold mb-2">Relevant folders</h3>
        {#if suggestions.length === 0}
          <p class="text-sm text-gray-500">No relevant folders.</p>
        {:else}
          <ul class="space-y-1">
            {#each suggestions as folder}
              <li>
                <button
                  type="button"
                  class={`w-full text-left text-sm px-2 py-1 rounded border cursor-pointer ${
                    activePath === folder.path
                      ? "bg-white border-blue-300"
                      : "border-transparent hover:bg-white hover:border-gray-200"
                  }`}
                  on:click={() => onOpenFolder(folder.path)}
                >
                  <span class="font-mono">{folder.path}</span>
                  <span class="text-gray-500 ml-2"
                    >({folder.matched_count})</span
                  >
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </div>

      <div>
        <h3 class="text-sm font-semibold mb-2">Subfolders</h3>
        {#if children.length === 0}
          <p class="text-sm text-gray-500">No subfolders.</p>
        {:else}
          <ul class="space-y-1">
            {#each children as child}
              <li>
                <button
                  type="button"
                  class="w-full text-left text-sm px-2 py-1 rounded border border-transparent hover:bg-white hover:border-gray-200 cursor-pointer"
                  on:click={() => onOpenFolder(child.path)}
                >
                  <span class="font-mono">{child.name}</span>
                  <span class="text-gray-500 ml-2">({child.matched_count})</span
                  >
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </div>
  </div>
{/if}
