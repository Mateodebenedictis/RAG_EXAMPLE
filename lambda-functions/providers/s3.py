import os
from boto3 import client
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
else:
    S3Client = object

content_bucket_name = os.getenv("CONTENT_S3_BUCKET_NAME", "")
layout_bucket_name = os.getenv("LAYOUT_S3_BUCKET_NAME", "")
generation_output_bucket_name = os.getenv("GENERATION_OUTPUT_S3_BUCKET_NAME", "")

s3_client: S3Client = client(
    "s3",
    use_ssl=True,
    verify=True,
)
