#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
  echo ".venv가 없습니다. 먼저 bash setup.sh 를 실행해 주세요."
  exit 1
fi

source .venv/bin/activate
python app.py
