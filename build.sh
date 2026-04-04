#!/bin/bash
set -e

# Render the SDD null-result paper
# Run from anywhere: ./research/build.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Compiling: ssrn-sdd-null-result.typ"
typst compile ssrn-sdd-null-result.typ ssrn-sdd-null-result.pdf

pages=$(pdfinfo ssrn-sdd-null-result.pdf 2>/dev/null | grep Pages | awk '{print $2}')
echo "  → ssrn-sdd-null-result.pdf ($pages pages)"
