import csv
import json
from pathlib import Path
from datetime import datetime


def save_experiment(metadata, rows, base_dir="data/experiments"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment_id = metadata["experiment_id"].strip().replace(" ", "_")
    folder = Path(base_dir) / f"{experiment_id}_{timestamp}"
    folder.mkdir(parents=True, exist_ok=True)

    csv_path = folder / "recording.csv"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    metadata_path = folder / "metadata.json"
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return folder, csv_path, metadata_path
