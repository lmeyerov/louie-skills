#!/usr/bin/env bash
set -euo pipefail

check_only=false
if [[ "${1:-}" == "--check-only" ]]; then
  check_only=true
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: must run inside a git repository" >&2
  exit 1
fi
cd "$(git rev-parse --show-toplevel)"

if command -v detect-secrets >/dev/null 2>&1; then
  detector=(detect-secrets)
elif command -v uvx >/dev/null 2>&1; then
  detector=(uvx --from detect-secrets detect-secrets)
elif command -v uv >/dev/null 2>&1; then
  detector=(uv tool run detect-secrets)
else
  echo "error: install detect-secrets, uvx, or uv to run secret detection" >&2
  exit 1
fi

if [[ ! -f .secrets.baseline ]]; then
  echo "error: .secrets.baseline is required" >&2
  exit 1
fi

baseline_copy="$(mktemp)"
trap "rm -f \"$baseline_copy\"" EXIT
cp .secrets.baseline "$baseline_copy"

if [[ "$check_only" == true ]]; then
  mapfile -d '' staged < <(git diff --cached --name-only -z --diff-filter=ACM)
  files=()
  for path in "${staged[@]}"; do
    [[ -z "$path" || "$path" == ".secrets.baseline" ]] && continue
    files+=("$path")
  done
  if [[ ${#files[@]} -eq 0 ]]; then
    echo "secret check: no staged files to scan"
    exit 0
  fi
  scan="$(mktemp)"
  trap 'rm -f "$scan" "$baseline_copy"' EXIT
  "${detector[@]}" scan --baseline "$baseline_copy" "${files[@]}" >"$scan" 2>/dev/null || true
  if [[ ! -s "$scan" ]]; then
    echo "secret check: passed"
    exit 0
  fi
  if python3 - "$scan" <<'PY'
import json
import sys
with open(sys.argv[1]) as f:
    result = json.load(f)
raise SystemExit(0 if not any(result.get("results", {}).values()) else 1)
PY
  then
    echo "secret check: passed"
    exit 0
  fi
  echo "error: new secrets detected in staged files" >&2
  exit 1
fi

"${detector[@]}" scan --baseline "$baseline_copy"
"${detector[@]}" scan --baseline "$baseline_copy" --only-verified
echo "secret check: passed"
