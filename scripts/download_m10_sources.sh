#!/usr/bin/env bash
set -euo pipefail

mkdir -p data/raw

echo "=== M10 SOURCE INGESTION (RETRY) ==="

# 1. UniMorph (verify already fetched)
if [ ! -s "data/raw/eng.unimorph" ]; then
    echo "Fetching UniMorph English..."
    curl -fLC - "https://raw.githubusercontent.com/unimorph/eng/master/eng" -o "data/raw/eng.unimorph"
else
    echo "UniMorph English verified."
fi

# 2. Open English WordNet (Clone OEWN YAML data repository directly)
if [ ! -d "data/raw/oewn_2025/src" ]; then
    echo "Fetching OEWN data repository via shallow clone..."
    rm -rf data/raw/oewn_2025 data/raw/oewn_2025.tar.gz
    git clone --depth 1 https://github.com/globalwordnet/english-wordnet.git data/raw/oewn_2025
else
    echo "OEWN directory verified."
fi

# 3. Kaikki.org English Dictionary JSONL
if [ ! -s "data/raw/kaikki.org-dictionary-English.jsonl" ]; then
    echo "Fetching Kaikki English dictionary JSONL..."
    curl -fLC - "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl" -o "data/raw/kaikki.org-dictionary-English.jsonl"
else
    echo "Kaikki JSONL verified."
fi

echo "=== M10 RAW CORPORA AUDIT ==="
ls -lh data/raw/eng.unimorph data/raw/kaikki.org-dictionary-English.jsonl
ls -d data/raw/oewn_2025
