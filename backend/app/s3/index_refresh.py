from concurrent.futures import ThreadPoolExecutor
from functools import partial
import json
import os
import fitz
from pathlib import Path
from typing import List, Dict, Optional
import time
from io import BytesIO
import sys
import meilisearch
import hashlib
from app.s3.refresh_status import (
    start_refresh,
    set_status,
    increment_listed,
    increment_processed,
    finish_refresh,
    fail_refresh
)

from mypy_boto3_s3 import S3Client
from app.s3.utils import get_public_client, parse_s3_uri
from app.schemas.meili_models import MeiliDocumentModel
from multiprocessing import Pool


# List of supported text file types for full-text indexing
TEXT_CONTENT_TYPES = ["text/plain", "text/css", "text/csv", "text/html", "text/markdown", "application/json"]
# Keyword parsing separation characters
SEPARATION_CHARACTERS = ["/", ",", "_", "-", " ", ".", "\n", ":", "\\", "(", ")", "[", "]", "=", ";", "—", "*", "\""]

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


def get_current_s3_objects(bucket_name: str, prefix: Optional[str] = None, s3_uri: Optional[str] = None):
    s3 = get_public_client()
    pager = s3.get_paginator("list_objects_v2")
    objects = []
    try:
        for page in pager.paginate(Bucket=bucket_name, Prefix=prefix or ""):
            contents = page.get("Contents", [])
            objects.extend(contents)
            if s3_uri is not None:
                increment_listed(s3_uri, len(contents))
    except Exception as e:
        print("Error fetching s3 objects:", e)

    return objects


def refresh_meili_index(bucket_name: str, prefix: Optional[str] = None, s3_uri: Optional[str] = None) -> None:
    # start tracking at object listing
    if s3_uri is not None:
        start_refresh(s3_uri, total=0, status="listing")

    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)
    current_files = get_current_s3_objects(bucket_name, prefix, s3_uri=s3_uri)

    index_objs = get_all_indexes()
    indexes = {f["uid"] for f in index_objs}

    if bucket_name in indexes:
        prev_documents = get_all_documents(bucket_name, prefix)
        
        prev_keys = [getattr(f, "Key") for f in prev_documents]
        curr_keys = [f["Key"] for f in current_files]

        # Detect new and removed files
        new_files = [f for f in current_files if f["Key"] not in prev_keys]
        removed_files = [f for f in prev_keys if f not in curr_keys]

        # compute total work up front
        total = len(new_files) + len(removed_files)

    else:
        new_files = current_files
        removed_files = []
        total = len(new_files)

    # track actual refresh
    if s3_uri is not None:
        set_status(s3_uri, status="running", total=total, reset_processed=True)

    try:
        if bucket_name in indexes:
            meili_client.index(bucket_name).update_sortable_attributes(
                ["Key", "Size", "LastModified"]
            )

            if new_files:
                add_files_to_index(bucket_name, new_files, s3_uri=s3_uri)
            if removed_files:
                remove_files_from_index(bucket_name, removed_files, s3_uri=s3_uri)

        else:
            # index doesn't exist, create a new index
            # object key includes invalid characters for primary key, create a hash of the key to use as the primary key instead
            # NOTE: this means that in order to access a specific document by key you must hash it first using get_doc_id
            meili_client.create_index(bucket_name, {"primaryKey": "ID"})
            meili_client.index(bucket_name).update_settings({
                "rankingRules": ["sort", "words", "typo", "proximity", "attribute", "exactness"],                
                "searchableAttributes": ["Tags", "Key", "Keywords"], # sorted in order of importance
                "filterableAttributes": ["ContentType", "Size", "StorageClass", "LastModified", "Prefix"],
                "sortableAttributes": ["Key", "Size", "LastModified"],
            })
            add_files_to_index(bucket_name, current_files, s3_uri=s3_uri)

        if s3_uri is not None:
            finish_refresh(s3_uri)

    except Exception as e:
        if s3_uri is not None:
            fail_refresh(s3_uri, str(e))
        raise


def create_index(index: str, file, meili_client: meilisearch.Client, s3_uri: Optional[str] = None) -> None:
    s3 = get_public_client()
    key = file["Key"]
    hashed_key = get_doc_id(key)
    head = s3.head_object(Bucket=index, Key=key)
    size = file["Size"]
    storage_class = file["StorageClass"]
    ctype = head.get("ContentType", "unknown")
    last_modified = int(file["LastModified"].timestamp())
    tags = [] # empty user tag array
    keywords = []
    prefixList = key.split("/")
    if len(prefixList) > 1: prefix = prefixList[0]
    else: prefix = None

    if ctype in TEXT_CONTENT_TYPES:
        keywords = get_keywords_from_text(index, key)
    elif ctype == "application/pdf":
        keywords = get_keywords_from_pdf(index, key)
    
    if len(keywords) == 0: keywords = get_keywords_from_key(key)
    
    new_document: MeiliDocumentModel = {
                    "ID": hashed_key,
                    "Key": key,
                    "LastModified": last_modified,
                    "Size": size,
                    "StorageClass": storage_class,
                    "ContentType": ctype,
                    "Keywords": keywords,
                    "Tags": tags,
                    "Prefix": prefix
                    }
    meili_client.index(index).add_documents([new_document])
    if s3_uri is not None:
        increment_processed(s3_uri, 1)

def add_files_to_index(index: str, new_files: List, s3_uri: Optional[str] = None) -> None:
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)

    create_with_args = partial(create_index, index, meili_client=meili_client, s3_uri=s3_uri)

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(create_with_args, new_files)


def remove_files_from_index(index: str, removed_keys: List[str], s3_uri: Optional[str] = None) -> None:
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)

    for key in removed_keys:
        hashed_key = get_doc_id(key)
        meili_client.index(index).delete_document(hashed_key)
        if s3_uri is not None:
            increment_processed(s3_uri, 1)


def get_keywords_from_key(key: str):
    replacements = str.maketrans({char:"," for char in SEPARATION_CHARACTERS})
    key = key.translate(replacements)
    keywords = list(set(key.split(",")))
    if keywords.count("") > 0: keywords.remove("")
    return keywords

def get_keywords_from_text(index: str, key: str):
    s3 = get_public_client()
    keywords = []
    try:
        response = s3.get_object(Bucket=index, Key=key)
        text_content = response["Body"].read().decode("utf-8")
        keywords = get_keywords_from_key(text_content)
    except Exception as e: 
        print(f"Error extracting text content from {key}", e)
        keywords = get_keywords_from_key(key)
    return keywords[:500] # only read up to 500 words to prevent index bloating on large text files

def get_keywords_from_pdf(index: str, key: str):
    s3 = get_public_client()
    keywords = []
    try:
        response = s3.get_object(Bucket=index, Key=key)
        pdf_stream = response["Body"].read()
        pdf_document = fitz.open("application/pdf", pdf_stream)
        for page in pdf_document:
            text = page.get_text("text")
            if text: keywords.extend(get_keywords_from_key(text))
            if len(keywords) > 500: break

    except Exception as e:
        print(f"Error extracting text content from {key}: {e}")
        keywords = get_keywords_from_key(key)
    return keywords[:500]


# TODO: move meilisearch utility functions to their own file
def get_doc_id(key: str):
    hash_object = hashlib.sha256(key.encode())
    hex_dig = hash_object.hexdigest()
    return(f"{hex_dig}")

def get_all_indexes():
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)

    limit = 20
    offset = 0
    total: int | None = None
    indexObjs = []
    while total is None or offset < total:
        temp = meili_client.get_raw_indexes({"limit": limit, "offset": offset})
        if total is None: total = temp["total"]
        offset += limit
        indexObjs.extend(temp["results"])

    return indexObjs

def get_all_documents(index: str, prefix: Optional[str] = None):
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)

    limit = 100
    offset = 0
    total: int | None = None
    documentObjs = []

    while total is None or offset < total:
        get_query = {
            "fields": ["Key"], 
            "limit": limit, 
            "offset": offset
        }
        if prefix is not None and prefix != "": get_query["filter"] = f"Prefix={prefix}"

        temp = meili_client.index(index).get_documents(get_query)
        if total is None: total = temp.total
        offset += limit
        documentObjs.extend(temp.results)

    return documentObjs


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python index_refresh.py <bucket_name>")
        sys.exit(1)

    bucket_name = sys.argv[1]
    refresh_search_index(bucket_name)
