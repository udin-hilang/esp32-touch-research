import queue
import threading
import time
from datetime import datetime

import serial
import serial.tools.list_ports


def list_serial_ports():
    return [(p.device, p.description) for p in serial.tools.list_ports.comports()]


def connect(port: str, baudrate: int):
    ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.05)
    time.sleep(1.5)  # ESP32 may reset when the serial port opens.
    ser.reset_input_buffer()
    return ser


class SerialSampleReader:
    """Continuously read serial lines and timestamp each valid sample on arrival."""

    def __init__(self, ser):
        self.ser = ser
        self._samples = queue.Queue()
        self._lock = threading.Lock()
        self._mode = "idle"
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)

    def start(self):
        self._thread.start()

    def _read_loop(self):
        while not self._stop.is_set():
            try:
                # Serial timeout is short, so start/stop and capture operations
                # wait at most one read timeout for this lock.
                with self._lock:
                    if self._stop.is_set() or not self.ser.is_open:
                        return
                    line = self.ser.readline()
                    if not line:
                        continue
                    received_at = datetime.now().isoformat(timespec="microseconds")
                    received_monotonic = time.monotonic()
                    if self._mode == "idle":
                        continue
                    try:
                        value = int(line.decode("utf-8", errors="ignore").strip())
                    except ValueError:
                        # Ignore startup text or malformed lines.
                        continue
                    self._samples.put({
                        "value": value,
                        "timestamp": received_at,
                        "received_monotonic": received_monotonic,
                    })
            except (serial.SerialException, OSError):
                return

    def _clear_samples(self):
        while True:
            try:
                self._samples.get_nowait()
            except queue.Empty:
                return

    def start_capture(self):
        with self._lock:
            self._clear_samples()
            self._mode = "capture"

    def stop_capture(self):
        with self._lock:
            self._mode = "idle"
            self._clear_samples()

    def start_recording(self):
        with self._lock:
            self._clear_samples()
            self._mode = "recording"

    def stop_recording(self):
        with self._lock:
            self._mode = "idle"
            samples = []
            while True:
                try:
                    samples.append(self._samples.get_nowait())
                except queue.Empty:
                    return samples

    def get_sample(self, timeout=None):
        try:
            return self._samples.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain_samples(self):
        samples = []
        while True:
            try:
                samples.append(self._samples.get_nowait())
            except queue.Empty:
                return samples

    def close(self):
        self._stop.set()
        try:
            self.ser.cancel_read()
        except (AttributeError, OSError, serial.SerialException):
            pass
        self._thread.join(timeout=1)
