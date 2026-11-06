import time
from datetime import datetime

import pandas as pd
import streamlit as st

from config import (
    DEFAULT_BAUDRATE,
    DEFAULT_SAMPLE_RATE_HZ,
    DEFAULT_BASELINE_SECONDS,
    DEFAULT_RECORDING_SAMPLE_COUNT,
)
from hardware.serial_manager import list_serial_ports, connect, SerialSampleReader
from hardware.firmware_manager import flash_firmware, FirmwareFlashError
from experiment.calibration import capture_baseline
from storage.csv_manager import save_experiment

st.set_page_config(page_title="ESP32 Touch Research DAQ", page_icon="📈", layout="wide")
st.title("ESP32 Capacitive Touch Research")
st.caption("Data Acquisition System • ESP32 USB Serial")

# Persistent session state
defaults = {
    "ser": None, "reader": None, "connected_port": None, "baseline": None,
    "baseline_samples": [], "recording": False, "recording_rows": [],
    "recording_start": None, "recording_sample_limit": None, "saved_path": None,
    "flashed_firmware": {}, "flash_result": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def append_received_samples(samples):
    """Add samples using the timestamps captured by the serial reader thread."""
    baseline = st.session_state.baseline
    limit = st.session_state.recording_sample_limit
    remaining = limit - len(st.session_state.recording_rows)
    for sample in samples[:max(0, remaining)]:
        sample_elapsed = max(
            0.0,
            sample["received_monotonic"] - st.session_state.recording_start,
        )
        value = sample["value"]
        st.session_state.recording_rows.append({
            "timestamp": sample["timestamp"],
            "elapsed_seconds": round(sample_elapsed, 6),
            "raw_value": value,
            "baseline": round(baseline, 4),
            "delta": round(value - baseline, 4),
            "delta_percent": round(abs(value - baseline) / abs(baseline) * 100, 4) if baseline else None,
            "material": material,
            "thickness_mm": float(thickness_mm),
            "trial": int(trial),
        })


def save_recording(sample_limit_reached=False):
    """Save the current touch recording and its selected sample limit."""
    st.session_state.recording = False
    flashed_firmware = st.session_state.flashed_firmware.get(st.session_state.connected_port, {})
    metadata = {
        "experiment_id": experiment_id,
        "operator": operator,
        "material": material,
        "thickness_mm": float(thickness_mm),
        "electrode": electrode,
        "trial": int(trial),
        "target_sample_rate_hz": int(sample_rate),
        "firmware_sample_rate_hz": flashed_firmware.get("sampling_rate_hz"),
        "firmware_baudrate": flashed_firmware.get("baudrate"),
        "firmware_fqbn": flashed_firmware.get("fqbn"),
        "firmware_flash_at": flashed_firmware.get("flashed_at"),
        "recording_sample_limit": int(st.session_state.recording_sample_limit),
        "baseline": float(st.session_state.baseline),
        "baseline_duration_seconds": int(baseline_seconds),
        "baseline_sample_count": len(st.session_state.baseline_samples),
        "baseline_samples": st.session_state.baseline_samples,
        "port": st.session_state.connected_port,
        "baudrate": int(baud),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        folder, csv_path, metadata_path = save_experiment(metadata, st.session_state.recording_rows)
        st.session_state.saved_path = str(folder)
        if sample_limit_reached:
            st.success(
                f"Batas {st.session_state.recording_sample_limit} sampel tercapai. "
                f"Data tersimpan: {folder}"
            )
        else:
            st.success(f"Data tersimpan: {folder}")
    except Exception as e:
        st.error(f"Gagal menyimpan data: {e}")

with st.sidebar:
    st.header("1. Device connection")
    ports = list_serial_ports()
    port_labels = [f"{p} — {d}" for p, d in ports]
    if ports:
        selected_label = st.selectbox("Serial port", port_labels)
        selected_port = ports[port_labels.index(selected_label)][0]
    else:
        selected_port = None
        st.warning("Port serial belum terdeteksi.")

    baud = st.number_input("Baud rate", min_value=1200, max_value=2000000,
                           value=DEFAULT_BAUDRATE, step=1200)
    board_fqbn = st.text_input("Arduino FQBN", value="esp32:esp32:esp32",
                               help="Contoh ESP32 klasik: esp32:esp32:esp32. Sesuaikan untuk board Anda.")

    c1, c2 = st.columns(2)
    if c1.button("Connect", disabled=(selected_port is None or st.session_state.recording)):
        try:
            if st.session_state.reader:
                st.session_state.reader.close()
                st.session_state.reader = None
            if st.session_state.ser and st.session_state.ser.is_open:
                st.session_state.ser.close()
            st.session_state.ser = connect(selected_port, int(baud))
            st.session_state.reader = SerialSampleReader(st.session_state.ser)
            st.session_state.reader.start()
            st.session_state.connected_port = selected_port
            st.session_state.baseline = None
            st.session_state.baseline_samples = []
            st.success(f"Terhubung ke {selected_port}")
        except Exception as e:
            st.error(f"Gagal terhubung: {e}")

    if c2.button("Disconnect", disabled=(st.session_state.ser is None or st.session_state.recording)):
        if st.session_state.reader:
            st.session_state.reader.close()
            st.session_state.reader = None
        try:
            st.session_state.ser.close()
        except Exception:
            pass
        st.session_state.ser = None
        st.session_state.connected_port = None
        st.session_state.baseline = None

    flash_result = st.session_state.flash_result
    if flash_result:
        if flash_result["success"]:
            st.success(flash_result["message"])
        else:
            st.error(flash_result["message"])
        if flash_result["reconnect_error"]:
            st.warning(flash_result["reconnect_error"])
        if flash_result["output"]:
            st.code(flash_result["output"][-8000:])
        st.session_state.flash_result = None

    is_connected = bool(st.session_state.ser and st.session_state.ser.is_open)
    st.write("Status:", "🟢 Connected" if is_connected else "🔴 Disconnected")
    st.divider()
    st.header("2. Experiment setup")
    experiment_id = st.text_input("Experiment ID", value="EXP-001")
    operator = st.text_input("Operator", value="")
    material = st.text_input("Material", value="Keramik")
    thickness_mm = st.number_input("Thickness (mm)", min_value=0.0, value=3.0, step=0.5)
    electrode = st.text_input("Electrode / Touch pin", value="T0")
    trial = st.number_input("Trial number", min_value=1, value=1, step=1)
    sample_rate = st.number_input("Target sampling rate (Hz)", min_value=1, max_value=1000,
                                  value=DEFAULT_SAMPLE_RATE_HZ)
    recording_sample_count = st.number_input(
        "Jumlah sampel touch recording",
        min_value=1,
        max_value=1000000,
        value=DEFAULT_RECORDING_SAMPLE_COUNT,
        step=10,
        disabled=st.session_state.recording,
        help="Recording berhenti dan tersimpan otomatis setelah jumlah sampel ini terkumpul.",
    )
    baseline_seconds = st.number_input("Baseline duration (seconds)", min_value=1, max_value=60,
                                       value=DEFAULT_BASELINE_SECONDS)

    if st.button(
        "Flash firmware ke ESP32",
        disabled=(selected_port is None or st.session_state.recording),
        help="Compile firmware dengan sampling rate dan baud yang dipilih, lalu upload ke port serial.",
    ):
        reconnect_after_flash = (
            st.session_state.ser is not None
            and st.session_state.ser.is_open
        )
        if reconnect_after_flash:
            if st.session_state.reader:
                st.session_state.reader.close()
                st.session_state.reader = None
            try:
                st.session_state.ser.close()
            except Exception:
                pass
            st.session_state.ser = None
            st.session_state.connected_port = None
            st.session_state.baseline = None
            st.session_state.baseline_samples = []

        flash_error = None
        flash_output = ""
        reconnect_error = None
        flash_succeeded = False
        with st.spinner(
            f"Compile dan upload firmware pada {selected_port} "
            f"({int(sample_rate)} Hz)..."
        ):
            try:
                flash_output = flash_firmware(
                    selected_port, int(sample_rate), int(baud), board_fqbn
                )
                flash_succeeded = True
                st.session_state.flashed_firmware[selected_port] = {
                    "sampling_rate_hz": int(sample_rate),
                    "baudrate": int(baud),
                    "fqbn": board_fqbn.strip(),
                    "flashed_at": datetime.now().isoformat(timespec="seconds"),
                }
            except FirmwareFlashError as e:
                flash_error = str(e)
            except Exception as e:
                flash_error = f"Gagal flash firmware: {e}"

        if reconnect_after_flash:
            try:
                st.session_state.ser = connect(selected_port, int(baud))
                st.session_state.reader = SerialSampleReader(st.session_state.ser)
                st.session_state.reader.start()
                st.session_state.connected_port = selected_port
            except Exception as e:
                st.session_state.ser = None
                st.session_state.reader = None
                st.session_state.connected_port = None
                reconnect_error = f"Koneksi ulang ke {selected_port} gagal: {e}"

        st.session_state.flash_result = {
            "success": flash_succeeded,
            "message": (
                flash_error
                or f"Firmware berhasil di-flash dengan sampling rate {int(sample_rate)} Hz."
            ),
            "reconnect_error": reconnect_error,
            "output": flash_output,
        }
        st.rerun()

    flash_status_port = st.session_state.connected_port if is_connected else selected_port
    selected_flash = st.session_state.flashed_firmware.get(flash_status_port, {})
    flash_matches = (
        selected_flash.get("sampling_rate_hz") == int(sample_rate)
        and selected_flash.get("baudrate") == int(baud)
        and selected_flash.get("fqbn") == board_fqbn.strip()
    )
    if selected_flash:
        st.caption(
            f"Terakhir di-flash: {selected_flash['sampling_rate_hz']} Hz, "
            f"{selected_flash['baudrate']} baud, {selected_flash['fqbn']}"
        )
        if not flash_matches:
            st.warning("Konfigurasi firmware yang terakhir di-flash berbeda dari setting saat ini.")
    else:
        st.info("Flash firmware untuk menerapkan sampling rate yang dipilih ke ESP32.")

st.header("3. Measurement")
st.info(
    "Prosedur: pasang material di atas elektroda tanpa disentuh → capture baseline "
    "→ sentuh permukaan material → mulai/akhiri recording."
)

m1, m2, m3 = st.columns(3)
m1.metric("Baseline", "—" if st.session_state.baseline is None else f"{st.session_state.baseline:.2f}")
m2.metric(
    "Samples in recording",
    f"{len(st.session_state.recording_rows)} / {st.session_state.recording_sample_limit}"
    if st.session_state.recording else len(st.session_state.recording_rows),
)
m3.metric("Device", st.session_state.connected_port or "Not connected")

col_a, col_b, col_c = st.columns(3)
if col_a.button("Capture baseline", disabled=not is_connected or st.session_state.recording):
    with st.spinner(f"Merekam baseline selama {baseline_seconds} detik. Pastikan material sudah terpasang dan belum disentuh."):
        try:
            baseline, values = capture_baseline(st.session_state.reader, int(baseline_seconds))
            st.session_state.baseline = baseline
            st.session_state.baseline_samples = values
            st.success(f"Baseline berhasil: {baseline:.2f} dari {len(values)} sampel.")
        except Exception as e:
            st.error(str(e))

if col_b.button("Start touch recording",
                disabled=(not is_connected or st.session_state.baseline is None or st.session_state.recording)):
    st.session_state.recording_rows = []
    st.session_state.recording_start = time.monotonic()
    st.session_state.recording_sample_limit = int(recording_sample_count)
    st.session_state.saved_path = None
    st.session_state.reader.start_recording()
    st.session_state.recording = True
    st.rerun()

if col_c.button("Stop & save", disabled=not st.session_state.recording):
    pending_samples = st.session_state.reader.stop_recording()
    append_received_samples(pending_samples)
    save_recording()

if st.session_state.recording:
    # The background reader timestamps each sample as its serial line arrives.
    new_samples = st.session_state.reader.drain_samples()
    now = time.monotonic()
    elapsed = now - st.session_state.recording_start
    append_received_samples(new_samples)
    if len(st.session_state.recording_rows) >= st.session_state.recording_sample_limit:
        # Stop receiving and discard any samples beyond the requested count.
        st.session_state.reader.stop_recording()
        save_recording(sample_limit_reached=True)
        st.rerun()
    if st.session_state.recording_rows:
        df_live = pd.DataFrame(st.session_state.recording_rows)
        st.line_chart(df_live.set_index("elapsed_seconds")[["raw_value"]], height=260)
        st.caption(f"Recording berjalan • {len(df_live)} sampel • {elapsed:.1f} detik")
    else:
        st.warning("Menunggu data serial dari ESP32...")
    time.sleep(0.15)
    st.rerun()
else:
    if st.session_state.recording_rows:
        df = pd.DataFrame(st.session_state.recording_rows)
        st.subheader("Recorded data")
        st.line_chart(df.set_index("elapsed_seconds")[["raw_value", "baseline"]], height=260)
        st.dataframe(df.tail(20), use_container_width=True)
        st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name="touch_recording.csv", mime="text/csv")
    elif st.session_state.baseline is not None:
        st.caption(f"Baseline tersimpan: {st.session_state.baseline:.2f}")

if st.session_state.saved_path:
    st.success(f"Folder eksperimen: {st.session_state.saved_path}")

st.divider()
st.caption("Prototype awal. Pastikan format firmware ESP32 mengirim satu angka integer di setiap baris Serial.")
