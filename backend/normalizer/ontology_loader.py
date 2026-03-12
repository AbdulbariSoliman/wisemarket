import csv
import os
from typing import Dict, List

BASE_DIR = "/workspaces/Swiss-Basket-AI/data/ontology"


def load_ontology(base_dir: str = BASE_DIR) -> Dict[str, List[dict]]:
    ontology_data: Dict[str, List[dict]] = {}

    for file in os.listdir(base_dir):
        if not file.endswith(".csv"):
            continue

        path = os.path.join(base_dir, file)
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            ontology_data[file.replace(".csv", "")] = list(reader)

    return ontology_data


if __name__ == "__main__":
    data = load_ontology()
    print(f"Loaded {len(data)} ontology categories")
    for key, rows in list(data.items())[:5]:
        print(f"{key}: {len(rows)} rows")
