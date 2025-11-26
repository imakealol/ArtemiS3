import json
import os
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import sys
import meilisearch
from app.s3.utils import get_public_client


def get_current_files_from_mock(bucket_name: str) -> List[Dict]:

    path = Path(bucket_name)
    if not path.exists():
        raise FileNotFoundError(f"Bucket '{bucket_name}' not found.")

    with open(path, "r") as f:
        data = json.load(f)

    return data



def refresh_search_index(bucket_name: str, cache_file: str = "index_cache.json"):
    """
    FR6 Prototype Demonstration

    Usage
    -----
    >>> # Refresh bucket search index
    >>> python index_refresh.py <NASA_Bucket_Name>
    """
    
    current_files = get_current_files_from_mock(bucket_name)

    cache_path = Path(cache_file)
    if cache_path.exists():
        with open(cache_path, "r") as f:
            previous_files = json.load(f)
    else:
        previous_files = []

    prev_keys = {f["Key"] for f in previous_files}
    curr_keys = {f["Key"] for f in current_files}

    # Detect new and removed files
    new_files = [f for f in current_files if f["Key"] not in prev_keys]
    removed_files = [f for f in previous_files if f["Key"] not in curr_keys]

    # Simulate updating the search index
    if new_files:
        print(f"Found {len(new_files)} new files:")
        for f in new_files:
            print(f"  + {f['Key']} (size: {f['Size']} bytes)")
    else:
        print("No new files found.")

    print()

    if removed_files:
        print(f"{len(removed_files)} files removed:")
        for f in removed_files:
            print(f"  - {f['Key']} (size: {f['Size']} bytes)")
    else:
        print("No files removed.")

    # Save the new state to disk
    with open(cache_path, "w") as f:
        json.dump(current_files, f, indent=2)


def get_current_s3_objects(bucket_name: str):
    s3 = get_public_client()
    objects = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=10)
    return objects["Contents"]


def refresh_meili_index(bucket_name: str):
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)
    current_files = get_current_s3_objects(bucket_name)

    indexObjs = meili_client.get_raw_indexes()["results"]
    indexes = {f["uid"] for f in indexObjs}

    if bucket_name in indexes:
        prev_documents = meili_client.index(bucket_name).get_documents({"fields": ["Key"]}).results
        print(meili_client.get_tasks())
        prev_keys = {f["Key"] for f in prev_documents}
        curr_keys = {f["Key"] for f in current_files}

        print(prev_documents, prev_keys, curr_keys)

        # Detect new and removed files
        new_files = [f for f in current_files if f["Key"] not in prev_keys]
        removed_files = [f for f in prev_keys if f not in curr_keys]

        if new_files:
            print(f"Adding {len(new_files)} new files to the index \"{bucket_name}\"")
            # add_files_to_index(bucket_name, new_files, meili_client)
        else:
            print("No new files found.")

        if removed_files:
            print(f"Removing {len(removed_files)} from the index \"{bucket_name}\"")
            # remove_files_from_index(bucket_name, removed_files, meili_client)
        else:
            print("No files removed.")
    else:
        # index doesn't exist, create a new index
        meili_client.create_index(bucket_name, {"primaryKey": "Key"})
        add_files_to_index(bucket_name, current_files, meili_client)


def add_files_to_index(index: str, new_files: List, meili_client: meilisearch.Client):
    s3 = get_public_client()

    for file in new_files:
        key = file["Key"]
        head = s3.head_object(Bucket=index, Key=key)
        size = file["Size"]
        ctype = head.get("ContentType", "unknown")
        last_modifed = f"{file["LastModified"].isoformat()
                    if isinstance(file["LastModified"], datetime)
                    else file["LastModified"]}"
        keywords = [] # extract keywords from key?
        tags = [] # empty user tag array
        
        new_document = {"Key": key,
                        "LastModified": last_modifed,
                        "Size": size,
                        "ContentType": ctype,
                        "keywords": keywords,
                        "tags": tags}
        res = meili_client.index(index).add_documents([new_document])
        print(res)


def remove_files_from_index(index: str, removed_files: List, meili_client: meilisearch.Client):
    for file in removed_files:
        print(file["Key"])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python index_refresh.py <bucket_name>")
        sys.exit(1)

    bucket_name = sys.argv[1]
    refresh_search_index(bucket_name)
