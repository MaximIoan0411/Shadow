#!/usr/bin/env bash
# Regenerează tipurile TypeScript ale frontend-ului din contractul API.
#   bash scripts/gen_types.sh        (din rădăcina repo-ului)
# openapi-typescript 7 cere TypeScript 5.x (cu TypeScript 7 se oprește cu „createKeywordTypeNode”).
set -euo pipefail
cd "$(dirname "$0")/../frontend"
npx --yes -p openapi-typescript@7 -p typescript@5.9 openapi-typescript ../contract/api/openapi.json -o src/lib/shadow-api.d.ts
echo "OK: frontend/src/lib/shadow-api.d.ts"
