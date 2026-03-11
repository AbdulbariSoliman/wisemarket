import os
import csv

# Absolute path to data/ontology
ONTOLOGY_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/ontology")
)

def load_ontologies():
    ontologies = {}

    for filename in os.listdir(ONTOLOGY_DIR):
        if not filename.endswith(".csv"):
            continue

        category = filename.replace(".csv", "")
        path = os.path.join(ONTOLOGY_DIR, filename)

        terms = []

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry = {
                    "term": row["term"].strip(),
                    "en": [x.strip().lower() for x in row["en"].split(";") if x.strip()],
                    "de": [x.strip().lower() for x in row["de"].split(";") if x.strip()],
                    "fr": [x.strip().lower() for x in row["fr"].split(";") if x.strip()],
                    "it": [x.strip().lower() for x in row["it"].split(";") if x.strip()],
                }
                terms.append(entry)

        ontologies[category] = terms

    return ontologies


if __name__ == "__main__":
    data = load_ontologies()
    print(f"Loaded {len(data)} ontology categories")
    for k, v in list(data.items())[:5]:
        print(f"{k}: {len(v)} terms")