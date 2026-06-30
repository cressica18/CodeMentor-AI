#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../frontend"

echo "=== CodeMentor AI — Frontend Setup ==="

if [ ! -d "node_modules" ]; then
  echo "Installing npm dependencies..."
  npm install
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

echo ""
echo "=== Starting Vite dev server ==="
echo "App will be at: http://localhost:5173"
echo ""
npm run dev
