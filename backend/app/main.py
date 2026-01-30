import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import meilisearch
from typing import List, Optional
from app.api.s3_routes import s3_router
from app.s3.index_refresh import refresh_meili_index
from app.s3.utils import parse_s3_uri

app = FastAPI(title="ArtemiS3 API")
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

meilisearch_url = os.getenv("MEILISEARCH_URL")
meili_client = meilisearch.Client(meilisearch_url)

# routers for various API endpoint functionalities
app.include_router(s3_router)

# index refresh async block
REFRESH_INTERVAL_SECONDS = int(os.getenv("REFRESH_INTERVAL_SECONDS", "3600"))
REFRESH_BUCKETS = os.getenv(
    "REFRESH_BUCKETS", 
    "s3://asc-pds-services,s3://asc-astropedia/Mars"#,s3://asc-pds-services/pigpen,s3://asc-astropedia"
)

def _parse_refresh_targets():
    return [s.strip() for s in REFRESH_BUCKETS.split(",") if s.strip()]

async def _index_refresh_loop():
    await asyncio.sleep(2) # let app start
    print("Starting index refresh loop...")
    while True:
        for s3_uri in _parse_refresh_targets():
            print(f"Trying to reindex: {s3_uri}")
            try:
                bucket, prefix = parse_s3_uri(s3_uri)
                await asyncio.to_thread(refresh_meili_index, bucket, prefix, s3_uri=s3_uri)

            except Exception as e:
                print(f"Refresh failed: s3_uri={s3_uri}, error={str(e)}")
        print(f"Waiting {REFRESH_INTERVAL_SECONDS} seconds...")
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)

@app.on_event("startup")
async def start_refresh_scheduler():
    asyncio.create_task(_index_refresh_loop())

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/api/test")
def test(name: str = "world") -> dict:
    return {"message": f"Hello, {name}!"}

@app.get("/api/meilisearch/test")
def test() -> dict:
    health = meili_client.health()
    return {"status": health}
