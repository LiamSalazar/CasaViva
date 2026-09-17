#!/usr/bin/env bash
set -Eeuo pipefail
readonly DOMAIN="${1:?Usage: wait-for-dns.sh DOMAIN EXPECTED_IPV4 [TIMEOUT_SECONDS]}"
readonly EXPECTED="${2:?Usage: wait-for-dns.sh DOMAIN EXPECTED_IPV4 [TIMEOUT_SECONDS]}"
readonly TIMEOUT="${3:-600}"
[[ "$TIMEOUT" =~ ^[0-9]+$ ]] || exit 2
deadline=$((SECONDS + TIMEOUT))
while (( SECONDS < deadline )); do
  mapfile -t addresses < <(getent ahostsv4 "$DOMAIN" 2>/dev/null | awk '{print $1}' | sort -u)
  for address in "${addresses[@]}"; do
    [[ "$address" == "$EXPECTED" ]] && { echo "DNS_READY $DOMAIN -> $EXPECTED"; exit 0; }
  done
  sleep 10
done
echo "DNS_NOT_READY: $DOMAIN does not resolve to $EXPECTED after ${TIMEOUT}s" >&2
exit 3
