#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../backend"

echo "=== CodeMentor AI — Backend Setup ==="

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

if [ ! -f ".env" ]; then
  echo "Copying .env.example → .env (fill in your API keys)"
  cp .env.example .env
fi

echo ""
echo "=== Starting FastAPI server ==="
echo "Docs will be at: http://localhost:8000/docs"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
