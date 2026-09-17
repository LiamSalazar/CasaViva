#!/usr/bin/env bash
set -Eeuo pipefail
[[ -r /sys/class/dmi/id/board_asset_tag ]] && grep -q '^i-' /sys/class/dmi/id/board_asset_tag || { echo "BLOCKED — run only on the Pilot EC2 instance" >&2; exit 2; }
readonly ROOT=/opt/casaviva
release="$(readlink -f "$ROOT/current")"
compose=(docker compose -p casaviva --env-file "$release/.env.production" -f "$release/docker-compose.yml")
"${compose[@]}" exec -T backend python - <<'PY'
import os, uuid, boto3
from botocore.exceptions import ClientError
from urllib.parse import urlparse
assert not os.environ.get("AWS_ACCESS_KEY_ID"), "static AWS_ACCESS_KEY_ID is forbidden"
session = boto3.Session()
credentials = session.get_credentials()
assert credentials and credentials.method in {"iam-role", "container-role"}, credentials.method if credentials else "missing"
frozen = credentials.get_frozen_credentials()
assert frozen.token, "instance-profile credentials must be temporary"
bucket = os.environ["AWS_STORAGE_BUCKET_NAME"]
prefix = os.environ.get("AWS_RUNTIME_TEST_PREFIX", "runtime-access-test")
key = f"{prefix}/{uuid.uuid4()}.txt"
s3 = session.client("s3")
s3.put_object(Bucket=bucket, Key=key, Body=b"casaviva-runtime-test")
assert s3.get_object(Bucket=bucket, Key=key)["Body"].read() == b"casaviva-runtime-test"
s3.delete_object(Bucket=bucket, Key=key)
denied_bucket = os.environ.get("AWS_DENY_TEST_BUCKET")
assert denied_bucket, "AWS_DENY_TEST_BUCKET must name an unrelated bucket for the denial test"
try:
    s3.get_object(Bucket=denied_bucket, Key="casaviva-deny-test")
except ClientError as error:
    assert error.response.get("Error", {}).get("Code") in {"AccessDenied", "403"}, error.response.get("Error", {}).get("Code")
else:
    raise AssertionError("instance role unexpectedly accessed unrelated bucket")
print("PASS temporary Instance Profile credentials and least-privilege S3 access")
PY
echo "SSM is consumed by the host deploy process; the backend container does not require Parameter Store access."
