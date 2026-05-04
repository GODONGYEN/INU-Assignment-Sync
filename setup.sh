#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
fi

mkdir -p data logs docs gui

echo "설치가 완료되었습니다."
echo "CLI 실행: source .venv/bin/activate && python main.py"
echo "GUI 실행: source .venv/bin/activate && python app.py"
