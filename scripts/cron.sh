#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/db.py --init --silent
python3 scripts/crawl.py
python3 scripts/db_export.py
python3 scripts/fill.py

# Commit & push (assumes git remote set + PAT if needed)
git add data/ docs/ site/data/models.json
if ! git diff --cached --quiet; then
  git commit -m "Automated quarterly refresh"
  git push origin main
fi