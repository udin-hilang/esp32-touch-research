import time


def capture_baseline(reader, duration_seconds=5):
    values = []
    reader.start_capture()
    start = time.monotonic()
    deadline = start + duration_seconds
    try:
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            sample = reader.get_sample(timeout=min(0.05, max(0, remaining)))
            if sample is not None:
                values.append(sample["value"])
    finally:
        reader.stop_capture()

    if len(values) < 3:
        raise RuntimeError(
            f"Baseline tidak cukup: hanya {len(values)} sampel. "
            "Periksa koneksi dan format data ESP32."
        )

    baseline = sum(values) / len(values)
    return baseline, values
