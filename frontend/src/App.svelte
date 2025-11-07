<script lang="ts">
  import {Search as SearchIcon} from "@lucide/svelte"

  let name = "ArtemiS3";
  async function ping() {
    const res = await fetch("/api/test?name=Svelte");
    const data = await res.json();
    alert(JSON.stringify(data))
  }
</script>

<main>
  <div class="w-screen h-screen p-2">
    <h1 class="text-red-500">Welcome to {name}</h1>
    <p>Frontend is up. NGINX proxies this page and /api to FastAPI.</p>
    <button on:click={ping} class="button">Test API</button>
    <h2>Search Page Prototype:</h2>
      <div class="aspect-16/9 mt-2 w-6xl border-2">
        <div class="border-b h-1/6 flex flex-col items-center justify-center">
          <h1>ArtemiS3</h1>
        </div>
        <div class="flex flex-col h-5/6 items-center justify-evenly">
          <div class="flex flex-col items-center">
            <div class="text-nowrap w-80 flex flex-col">
              <input class="w-full shadow" placeholder="Search for Files" />
              <SearchIcon class="relative left-[calc(100%-28px)] bottom-[calc(100%-28px)] text-gray-500" />
            </div>
          </div>
          <div class="w-4/5 text-center border h-3/5">
            results
          </div>
        </div>
      </div>
  </div>
</main>

<style>
  main {
    font-family: system-ui, sans-serif;
    padding: 2rem
  }
</style>
