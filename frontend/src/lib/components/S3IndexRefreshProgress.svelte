<script lang="ts">
  import { onDestroy } from "svelte";
  import { getRefreshStatus } from "../api/s3";
  import type { MeilisearchRefreshStatus } from "../schemas/meilisearch";

  export let s3Uri = "";

  let status: MeilisearchRefreshStatus = {
    status: "idle",
    processed: 0,
    total: 0,
    percent: 0,
  };
  let pollId: number | null = null;
  let error: string | null = null;

  async function pollOnce() {
    if (!s3Uri) return;
    try {
      status = await getRefreshStatus(s3Uri);
      error = null;
    } catch (err) {
      error = err instanceof Error ? err.message : "Unknown error occurred";
    }
  }

  function startPolling() {
    stopPolling();
    pollOnce();
    pollId = window.setInterval(pollOnce, 1500);
  }

  function stopPolling() {
    if (pollId !== null) {
      clearInterval(pollId);
      pollId = null;
    }
  }

  if (s3Uri) {
    startPolling();
  } else {
    stopPolling();
    status = {
      status: "idle",
      processed: 0,
      total: 0,
      percent: 0,
    };
  }

  // might be worth changing later...
  if (
    status.status === "done" ||
    status.status === "error" ||
    status.status === "idle"
  ) {
    stopPolling();
  }

  onDestroy(stopPolling);
</script>

{#if s3Uri}
  {#if status.status === "running"}
    <div class="mt-2 w-full">
      <div class="text-sm text-gray-600 mb-1">
        Refreshing index: {status.processed}/{status.total} ({status.percent}%)
      </div>
      <div class="h-2 bg-gray-200 rounded">
        <div
          class="h-2 bg-blue-600 rounded"
          style={`width: ${status.percent}`}
        ></div>
      </div>
    </div>
  {:else if status.status === "error"}
    <div class="mt-2 text-sm text-red-600">
      Refresh error: {status.message || "Unknown error occurred"}
    </div>
  {/if}
{/if}
