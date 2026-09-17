#!/usr/bin/env bash
set -Eeuo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/out-a" "$tmp/out-b" "$tmp/root"
sha_a=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
sha_b=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
"$repo/scripts/build-ops-bundle.sh" "$sha_a" "$tmp/out-a" >/dev/null
"$repo/scripts/install-ops-bundle.sh" "$sha_a" "file://$tmp/out-a" "$tmp/root" >/dev/null
[[ "$(cat "$tmp/root/shared/current_ops_release")" == "$sha_a" ]]
[[ "$(cat "$tmp/root/current-ops/OPS_RELEASE")" == "$sha_a" ]]
"$repo/scripts/build-ops-bundle.sh" "$sha_b" "$tmp/out-b" >/dev/null
"$repo/scripts/install-ops-bundle.sh" "$sha_b" "file://$tmp/out-b" "$tmp/root" >/dev/null
[[ "$(cat "$tmp/root/shared/current_ops_release")" == "$sha_b" ]]
[[ "$(cat "$tmp/root/shared/previous_ops_release")" == "$sha_a" ]]
cp "$tmp/out-b/casaviva-ops-$sha_b.tar.gz" "$tmp/out-b/tampered"
printf 'tamper' >> "$tmp/out-b/casaviva-ops-$sha_b.tar.gz"
if "$repo/scripts/install-ops-bundle.sh" "$sha_b" "file://$tmp/out-b" "$tmp/root" >/dev/null 2>&1; then
  echo "Tampered bundle was accepted" >&2
  exit 1
fi
mv "$tmp/out-b/tampered" "$tmp/out-b/casaviva-ops-$sha_b.tar.gz"
echo "PASS ops bundle checksum and current/previous tracking"
