<script lang="ts">
  import { X } from "@lucide/svelte";

  export let editing: string | null;
  export let localTags: string[];
  export let setEditing: (key: string | null) => void;
  export let submitTags: (key: string, tags: string[]) => Promise<void>;

  let tagInput = "";

  $: clearInput(editing);
  function clearInput(_editing: string | null) {
    tagInput = "";
  }

  function keydown(e: KeyboardEvent) {
    e.stopPropagation();
    if (e.key === "Escape") {
      setEditing(null);
    } else if (e.key === "Enter") {
      e.preventDefault();
      addToLocal();
    }
  }
  function modalAction(node: HTMLElement) {
    const returnFn: Array<() => void> = [];
    node.addEventListener("keydown", keydown);
    node.focus();
    returnFn.push(() => {
      node.removeEventListener("keydown", keydown);
    });
    return {
      destroy: () => returnFn.forEach((fn) => fn()),
    };
  }
  function addToLocal() {
    localTags =
      localTags.includes(tagInput) || tagInput === ""
        ? localTags
        : [...localTags, tagInput];
    tagInput = "";
  }
</script>

{#if editing}
  <div
    class="fixed w-screen h-screen inset-0 flex items-center justify-center"
    role="dialog"
    aria-modal="true"
    tabindex="0"
    use:modalAction
  >
    <div
      class="absolute w-screen h-screen z-99 bg-black/20 backdrop-blur-xs animate-in fade-in duration-200"
      role="dialog"
      tabindex="-1"
      on:click={() => setEditing(null)}
      on:keypress={(e: KeyboardEvent) => {
        console.log(e);
        setEditing(null);
      }}
    ></div>
    <div
      class="border border-gray-400 shadow-lg bg-white rounded-lg z-100 max-w-lg"
    >
      <div
        class="flex p-1 items-center justify-between border-b border-gray-300 text-xl"
      >
        <span class="size-6"></span>
        <span>Edit File Tags</span>
        <button
          class="icon-button text-gray-500! hover:text-gray-600!"
          on:click={() => setEditing(null)}
        >
          <X size={24} />
        </button>
      </div>
      <div class="py-4 px-8 flex flex-col items-left gap-4">
        <div>
          Editing tags for:
          <div
            class="overflow-x-auto border border-gray-300 rounded p-2 pb-3 bg-slate-50"
          >
            {editing}
          </div>
        </div>
        <form
          class="flex items-center gap-2 text-nowrap"
          on:submit={addToLocal}
        >
          Enter Tags:
          <input
            class="w-full"
            bind:value={tagInput}
            placeholder="mars-rover-2020"
          />
          <button type="submit" class="button">Add Tag</button>
        </form>
        {#if localTags.length > 0}
          <div
            class="w-full h-fit border border-gray-300 bg-slate-100 rounded-lg py-2 px-4 flex gap-2 flex-wrap"
          >
            {#each localTags as tag}
              <div
                class="pl-2 border border-gray-400 rounded-full flex items-center gap-1 bg-white"
              >
                <span>{tag}</span>
                <button
                  title="Delete Tag"
                  class="border-gray-300 pr-1 text-gray-500 hover:text-gray-700 cursor-pointer"
                  value={tag}
                  on:click={(e) =>
                    (localTags = localTags.filter(
                      (tag) => tag !== e.currentTarget.value,
                    ))}
                >
                  <X size={20} />
                </button>
              </div>
            {/each}
          </div>
        {/if}
        <button
          class="button w-fit self-center"
          on:click={async () => {
            await submitTags(editing, localTags);
          }}>Save Changes</button
        >
      </div>
    </div>
  </div>
{/if}
