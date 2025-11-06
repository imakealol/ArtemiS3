import argparse
from s3 import parse_s3_uri, get_public_client

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("s3_uri", 
                    help="s3://<bucket>/<prefix>")
    ap.add_argument("--limit", 
                    type=int, 
                    default=50, 
                    help="max objects to process")
    args = ap.parse_args()

    bucket, prefix = parse_s3_uri(args.s3_uri)
    s3 = get_public_client()
    processed = 0

    pager = s3.get_paginator("list_objects_v2")
    for page in pager.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            print(f"[KEY] {key}")
            head = s3.head_object(Bucket=bucket, Key=key)
            size = obj["Size"]
            ctype = head.get("ContentType", "unknown")
            last_mod = obj["LastModified"]
            print(f"[METADATA] {key} | size={size} | type={ctype} | last_modified={last_mod}")

            processed += 1
            if processed >= args.limit:
                break
        if processed >= args.limit:
            break

if __name__ == "__main__":
    main()
