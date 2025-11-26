<script>
    let s3Bucket = "";
    async function refreshIndex() {
        const queries = new URLSearchParams();
        queries.set("s3_uri", s3Bucket)
        fetch(`/api/s3/refresh?${queries.toString()}`)
    }
</script>

<main>
    <div class="p-4 my-2 border-1 w-fit rounded">
        Index Refresh test:
        <input id="s3Bucket" placeholder="s3://bucket/prefix" bind:value={s3Bucket} required/>
        <button class="button" onclick={refreshIndex}>Refresh Index</button>
    </div>
</main>