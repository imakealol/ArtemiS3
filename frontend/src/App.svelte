<script lang="ts">
  import {Search as SearchIcon, ChevronDown } from "@lucide/svelte"

  let name = "ArtemiS3";
  async function ping() {
    const res = await fetch("/api/test?name=Svelte");
    const data = await res.json();
    alert(JSON.stringify(data))
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
            <div class="w-full flex justify-end">
              <button class="expandable">
                <ChevronDown class="size-5 text-gray-600" />Filter<span class="size-5"></span>
              </button>
            </div>
            <div class="w-full h-full text-center border">
              results
            </div>
          </div>
        </div>
      </div>
  </div>
</main>
