#!/bin/bash
set -e
cd /home/clem/pyjoal

# VERSION UPDATE
bash update_version.sh 1.11.2

# RUN TESTS LOCALLY
echo ""
echo "🧪 Running backend tests..."
cd backend
source venv/bin/activate
python -m pytest tests/ -x --tb=line 2>&1 | tail -30

# FLAKE8
echo ""
echo "🔍 Flake8..."
flake8 app/ --max-line-length=120 --extend-ignore=E203,W503,E501,W291,W292,W293,W391,E128,E302,E303,E305,E402 --count 2>&1 | tail -3

cd /home/clem/pyjoal

# CLEANUP TEMP FILES
rm -f _ver_test.sh _fix_final.sh

# COMMIT
git add -A
git diff --cached --stat
git commit -m "feat: v1.11.2 - peer speed tiers, inline metadata, totalUploaded fix" -m "- Configurable peer-based speed tiers (T1: 0-20p=15%, T2: 20-100p=60%, T3: 100+p=100%)
- Inline torrent metadata (creator · tracker · date)
- Fix totalUploaded ResponseValidationError (int casting)
- Version 1.11.2"

# TAG & PUSH
git tag -a v1.11.2 -m "Release v1.11.2"
git push origin master --tags 2>&1

echo ""
echo "✅ v1.11.2 DONE"
