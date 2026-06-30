#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../backend"
source .venv/bin/activate

echo "=== Running Phase 1 tests ==="
pytest tests/test_phase1.py -v
