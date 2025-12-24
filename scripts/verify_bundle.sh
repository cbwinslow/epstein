#!/usr/bin/env bash
set -euo pipefail

# Verify that files in docs/files/* match corresponding files in the repo root
# Usage: scripts/verify_bundle.sh [DOCS_DIR]

DOCS_DIR=${1:-docs/files}
ROOT_DIR=$(pwd)

missing=0
mismatch=0

echo "Verifying bundles under $DOCS_DIR"

shopt -s globstar
for src in "$DOCS_DIR"/**; do
    [ -f "$src" ] || continue
    rel=${src#${DOCS_DIR}/}
    target="$ROOT_DIR/$rel"
    if [ ! -f "$target" ]; then
        echo "MISSING: $target (referenced by $src)"
        missing=$((missing+1))
        continue
    fi
    if ! diff -u "$target" "$src" >/dev/null; then
        echo "MISMATCH: $rel"
        mismatch=$((mismatch+1))
    fi
done

if [ $missing -ne 0 ] || [ $mismatch -ne 0 ]; then
    echo "\nBundle verification failed: $missing missing, $mismatch mismatched"
    exit 2
fi

echo "All bundles verified OK."
exit 0
