import re
import boto3
from botocore import UNSIGNED
from botocore.client import Config
from mypy_boto3_s3 import S3Client
from typing import Optional, List


def parse_s3_uri(uri: str) -> tuple[str, str]:
    match_ = re.match(r"^s3://([^/]+)(?:/(.*))?$", uri)
    if not match_:
        raise ValueError(f"Invalid S3 URI: {uri}")
    return match_.group(1), match_.group(2) or ""


def get_public_client(region: Optional[str] = None) -> S3Client:
    return boto3.client("s3", region_name=region,
                        config=Config(signature_version=UNSIGNED))


def generate_preview_url(bucket: str, key: str, expires_in=300):
    try:
        s3_client = boto3.client(
            "s3",
            config=Config(signature_version='s3v4')
        )

        url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket,
                "Key": key,
            },
            ExpiresIn=expires_in,
        )
        return url
    except Exception as e:
        # Ams credentials failed
        print(f"Presigned URL failed: {e}")
        # failsafe, try public
        return f"https://{bucket}.s3.amazonaws.com/{key}"


def normalize_s3_path(path: Optional[str]) -> str:
    """Replace any '//' with '/', strips whitespace."""
    if not path:
        return ""

    norm = path.strip().strip("/")
    while "//" in norm:
        norm = norm.replace("//", "/")
    return norm


def key_parent_path(key: str) -> str:
    """Gets the parent path key, folder above actual file."""
    key = normalize_s3_path(key)
    if "/" not in key:
        return ""
    return key.rsplit("/", 1)[0]


def key_filename(key: str) -> str:
    """Gets the actual filename from key."""
    key = normalize_s3_path(key)
    return key.rsplit("/", 1)[-1] if key else ""


def parent_ancestors(parent_path: str) -> List[str]:
    """Generates list of all parent path's ancestors."""
    if not parent_path:
        return []
    parent_path = normalize_s3_path(parent_path)
    parts = parent_path.split("/")
    return ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]


def path_depth(path: str) -> int:
    """Calculates the path depth."""
    path = normalize_s3_path(path)
    return 0 if not path else len(path.split("/"))


def escape_meili_filter_val(val: str) -> str:
    """Correctly format Meilisearch filter value."""
    return val.replace("\\", "\\\\").replace("'", "\\'")


def build_subtree_filter(path: str) -> str:
    """Builds subtree filter command."""
    p = normalize_s3_path(path)
    e = escape_meili_filter_val(p)
    return f"(Ancestors = '{e}' OR ParentPath = '{e}')"
