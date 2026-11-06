import shutil
import subprocess
import tempfile
from pathlib import Path


class FirmwareFlashError(RuntimeError):
    """Raised when Arduino CLI cannot compile or upload the firmware."""


def flash_firmware(port: str, sampling_rate_hz: int, baudrate: int, fqbn: str) -> str:
    """Compile and upload the touch firmware with the selected serial settings."""
    if not 1 <= int(sampling_rate_hz) <= 1000:
        raise FirmwareFlashError("Sampling rate harus antara 1 dan 1000 Hz.")
    if not fqbn.strip():
        raise FirmwareFlashError("Arduino FQBN tidak boleh kosong.")

    arduino_cli = shutil.which("arduino-cli")
    if not arduino_cli:
        raise FirmwareFlashError(
            "arduino-cli tidak ditemukan. Install Arduino CLI, tambahkan ke PATH, "
            "lalu install core ESP32 yang sesuai dengan board."
        )

    template_path = Path(__file__).resolve().parents[1] / "firmware_example.ino"
    source = template_path.read_text(encoding="utf-8")
    replacements = {
        "#define SAMPLE_RATE_HZ 10": f"#define SAMPLE_RATE_HZ {int(sampling_rate_hz)}",
        "#define SERIAL_BAUD_RATE 115200": f"#define SERIAL_BAUD_RATE {int(baudrate)}",
    }
    for marker, replacement in replacements.items():
        if source.count(marker) != 1:
            raise FirmwareFlashError(
                f"Template firmware tidak memiliki tepat satu konfigurasi: {marker}"
            )
        source = source.replace(marker, replacement, 1)

    try:
        with tempfile.TemporaryDirectory(prefix="esp32_touch_firmware_") as temp_dir:
            sketch_dir = Path(temp_dir) / "ESP32TouchDAQ"
            sketch_dir.mkdir()
            (sketch_dir / "ESP32TouchDAQ.ino").write_text(source, encoding="utf-8")
            command = [
                arduino_cli,
                "compile",
                "--upload",
                "--fqbn",
                fqbn.strip(),
                "--port",
                port,
                str(sketch_dir),
            ]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
    except subprocess.TimeoutExpired as error:
        output = "\n".join(
            part.decode(errors="replace") if isinstance(part, bytes) else part
            for part in (error.stdout, error.stderr)
            if part
        )
        raise FirmwareFlashError(
            "Compile atau upload melebihi batas waktu 5 menit.\n" + output
        ) from error
    except OSError as error:
        raise FirmwareFlashError(f"Gagal menjalankan arduino-cli: {error}") from error

    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    if result.returncode != 0:
        raise FirmwareFlashError(output or f"arduino-cli keluar dengan kode {result.returncode}.")
    return output or "Firmware berhasil di-compile dan di-upload."
