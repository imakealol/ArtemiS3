import re
import boto3
from botocore import UNSIGNED
from botocore.client import Config
from mypy_boto3_s3 import S3Client
from typing import Optional

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