#!/bin/bash
# Finder-friendly entry point; the launcher lives in scripts/.
exec "$(cd -- "$(dirname -- "$0")" && pwd)/scripts/open-studio.command" "$@"
