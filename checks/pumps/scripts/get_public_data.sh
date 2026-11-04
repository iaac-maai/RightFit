#!/usr/bin/env bash
# Downloads the public parts of the RightFit dataset into ./public
# Run from the kit folder:  bash scripts/get_public_data.sh
set -euo pipefail
mkdir -p public/regulations public/codeaccord public/doclaynet

echo "1/3 CODE-ACCORD: 862 regulation sentences labelled for rule extraction (England + Finland)"
git clone --depth 1 https://github.com/Accord-Project/CODE-ACCORD public/codeaccord || echo "   clone failed: get it from https://doi.org/10.5281/zenodo.10210022"

echo "2/3 EU regulations (PDF, official EUR-Lex)"
get() { curl -sSL -o "public/regulations/$1" "$2" && echo "   $1" || echo "   failed: $2"; }
get EU_547-2012_water_pumps.pdf      "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32012R0547"
get EU_2019-1781_motors.pdf          "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32019R1781"
get EU_641-2009_circulators.pdf      "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32009R0641"
get EU_2006-42_machinery.pdf         "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32006L0042"
get EU_1253-2014_ventilation.pdf     "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014R1253"
get EU_2024-573_fgas.pdf             "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32024R0573"
get ES_CTE_DB-HS_salubridad.pdf      "https://www.codigotecnico.org/pdf/Documentos/HS/DBHS.pdf"

echo "3/3 DocLayNet sample (page layouts for pre-training the page sorter; full set is ~30 GB)"
python3 - <<'PY' || echo "   install first: pip install datasets"
from datasets import load_dataset
ds = load_dataset("docling-project/DocLayNet-v1.1", split="train", streaming=True)
manuals = (x for x in ds if x.get("doc_category") in ("manuals", "patents"))
import json, itertools, os
with open("public/doclaynet/manuals_sample.jsonl", "w") as f:
    for x in itertools.islice(manuals, 500):
        f.write(json.dumps({k: v for k, v in x.items() if k != "image"}, default=str) + "\n")
print("   public/doclaynet/manuals_sample.jsonl (500 pages, no images)")
PY
echo "done -> ./public"
