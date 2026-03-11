import os
import csv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

HEADER = ["term", "en", "de", "fr", "it"]

def normalize_row(row):
    while len(row) < 5:
        row.append("")
    return row[:5]

def enrich_row(row):
    term, en, de, fr, it = normalize_row(row)

    if not de:
        de = en
    if not fr:
        fr = en
    if not it:
        it = en

    return [term, en, de, fr, it]

for filename in os.listdir(BASE_DIR):
    if not filename.endswith(".csv"):
        continue

    path = os.path.join(BASE_DIR, filename)
    rows = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        existing = list(reader)

    if not existing:
        rows.append(HEADER)
    else:
        rows.append(HEADER)

        for row in existing[1:]:
            if not row:
                continue
            rows.append(enrich_row(row))

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print(f"Updated: {filename}")

print("\n✅ All ontology CSVs normalized and multilingual.")