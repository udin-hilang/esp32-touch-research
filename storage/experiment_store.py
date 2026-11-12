"""Read, update, and serialize experiment folders stored on disk."""

import csv
import json
import math
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "experiments"


def _parse_csv_value(value):
    if value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            number = float(value)
            return number if math.isfinite(number) else None
        except (TypeError, ValueError):
            return value


def read_samples(csv_path):
    """Return CSV rows as JSON-friendly dictionaries with numeric values parsed."""
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        return []
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        return [
            {key: _parse_csv_value(value) for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def list_experiments(data_dir=DEFAULT_DATA_DIR):
    """Load every experiment folder, including folders with incomplete files."""
    data_dir = Path(data_dir).resolve()
    if not data_dir.is_dir():
        return []

    experiments = []
    for folder in sorted((p for p in data_dir.iterdir() if p.is_dir()), reverse=True):
        metadata_path = folder / "metadata.json"
        csv_path = folder / "recording.csv"
        errors = []
        metadata = {}
        if metadata_path.is_file():
            try:
                with metadata_path.open("r", encoding="utf-8") as handle:
                    metadata = json.load(handle)
                if not isinstance(metadata, dict):
                    errors.append("metadata.json harus berupa object JSON")
                    metadata = {}
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"metadata.json tidak dapat dibaca: {exc}")
        else:
            errors.append("metadata.json tidak ditemukan")

        samples = []
        if csv_path.is_file():
            try:
                samples = read_samples(csv_path)
            except (OSError, csv.Error, UnicodeDecodeError) as exc:
                errors.append(f"recording.csv tidak dapat dibaca: {exc}")
        else:
            errors.append("recording.csv tidak ditemukan")

        experiments.append({
            "folder": folder.name,
            "path": folder,
            "metadata": metadata,
            "samples": samples,
            "errors": errors,
        })
    return experiments


def experiment_json(experiment):
    """Create the combined JSON representation used by downloads and the API."""
    return {
        "folder": experiment["folder"],
        "metadata": experiment["metadata"],
        "samples": experiment["samples"],
    }


def save_metadata(experiment, metadata):
    """Atomically replace an experiment's metadata JSON."""
    folder = Path(experiment["path"]).resolve()
    temp_path = folder / ".metadata.json.tmp"
    target_path = folder / "metadata.json"
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    temp_path.replace(target_path)


def delete_experiment(experiment, data_dir=DEFAULT_DATA_DIR):
    """Remove one experiment folder after ensuring it is inside the data directory."""
    root = Path(data_dir).resolve()
    folder = Path(experiment["path"]).resolve()
    if folder.parent != root or not folder.is_dir():
        raise ValueError("Folder eksperimen tidak valid atau berada di luar direktori data.")
    shutil.rmtree(folder)
