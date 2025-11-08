<script lang="ts">
  import { onMount } from "svelte";

  let name = "ArtemiS3";

  let dropdownOpen = false;
  let selectedTypes: string[] = [];
  let dateValue = "";
  let dateCondition = "before";

  function toggleDropdown() {
    dropdownOpen = !dropdownOpen;
  }

  function toggleType(type: string) {
    if (selectedTypes.includes(type)) {
      selectedTypes = selectedTypes.filter(t => t !== type);
    } else {
      selectedTypes = [...selectedTypes, type];
    }
  }

  async function sendFilter() {
    const res = await fetch("http://127.0.0.1:8000/api/filter", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selected_types: selectedTypes, date: dateValue, condition: dateCondition })
    });
    const data = await res.json();
    console.log("Response from backend:", data);
  }
</script>

<main>
  <h1>Welcome to {name}</h1>
  <p>Frontend is up. NGINX proxies this page and /api to FastAPI.</p>
  <button on:click={ping}>Test API</button>
    <!-- Dropdown button -->
  <div class="flex items-center gap-4 mt-4">

    <div class="relative">
    <button on:click={toggleDropdown} class="border p-2 rounded bg-gray-100 hover:bg-gray-200">
      Filter ▼
    </button>

    {#if dropdownOpen}
      <div class="absolute mt-1 border rounded bg-white shadow p-4 w-64 z-10">
        
        <!-- File Type Section with Checkboxes -->
        <div class="mb-4">
          <h4 class="font-semibold mb-2">File Types</h4>
          <div class="flex flex-col gap-1">
            <label class="flex items-center gap-2">
              <input type="checkbox" value="txt" checked={selectedTypes.includes("txt")} on:change={() => toggleType("txt")} />
              TXT
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" value="png" checked={selectedTypes.includes("png")} on:change={() => toggleType("png")} />
              PNG
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" value="jpeg" checked={selectedTypes.includes("jpeg")} on:change={() => toggleType("jpeg")} />
              JPEG
            </label>
          </div>
        </div>

        <!-- Date Section -->
        <div class="mb-4">
          <h4 class="font-semibold mb-2">Date</h4>
          <div class="flex gap-2 items-center">
            <input type="text" placeholder="dd/mm/yyyy" bind:value={dateValue} class="border p-1 rounded w-32" />
            <select bind:value={dateCondition} class="border p-1 rounded">
              <option value="before">Before</option>
              <option value="after">After</option>
            </select>
          </div>
        </div>

        <!-- Placeholder Section -->
        <div>
          <h4 class="font-semibold mb-2">Third Section</h4>
          <div class="border p-2 rounded text-gray-400">Coming soon...</div>
        </div>

        <button on:click={sendFilter} class="mt-4 bg-blue-500 text-white p-2 rounded w-full">Send Filter</button>
      </div>
    {/if}
    </div>

    <!-- Search bar -->
    <input type="text" placeholder="Search for files" class="border p-2 rounded flex-1" />
  </div>
</main>

<style>
  main {
    font-family: system-ui, sans-serif;
    padding: 2rem;
  }
</style>
