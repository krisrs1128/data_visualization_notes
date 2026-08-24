#!/usr/bin/env bash
# Renders every .qmd in this directory to .html in place, so the compiled
# pages sit next to their source files and can be served straight off
# GitHub Pages (repo root as the Pages source).
set -uo pipefail

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$dir"

failures=()
for f in *.qmd; do
  echo "== Rendering $f =="
  if ! quarto render "$f"; then
    failures+=("$f")
  fi
  echo
done

if [ ${#failures[@]} -eq 0 ]; then
  echo "All files rendered successfully."
else
  echo "Failed to render:"
  printf '  %s\n' "${failures[@]}"
  exit 1
fi
