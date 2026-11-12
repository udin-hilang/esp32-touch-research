# ESP32 Capacitive Touch Research DAQ

Prototype aplikasi Python untuk:
- koneksi ESP32 melalui USB Serial;
- konfigurasi metadata material, ketebalan, elektroda, dan trial;
- capture baseline saat material sudah terpasang tetapi belum disentuh;
- merekam respons saat permukaan material disentuh;
- menghitung delta terhadap baseline;
- menampilkan grafik dan menyimpan CSV + metadata JSON.

## 1. Persiapan

Disarankan Python 3.10 atau lebih baru.

```bash
python -m venv .venv
```

Aktifkan environment:
- Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
- Linux/macOS: `source .venv/bin/activate`

Install:
```bash
pip install -r requirements.txt
```

## 2. Firmware

Firmware dapat di-upload dari sidebar aplikasi melalui tombol **Flash firmware ke ESP32**.
Install Arduino CLI, tambahkan ke `PATH`, lalu install core ESP32 standar dengan:

```bash
arduino-cli core update-index
arduino-cli core install esp32:esp32
```

Isi Arduino FQBN board Anda di sidebar (default `esp32:esp32:esp32`). Nilai sampling rate dan
baud dari UI digunakan saat firmware di-compile dan di-upload.
Pastikan Serial Monitor ditutup sebelum proses flash dimulai. Tombol flash akan menutup sementara
koneksi aplikasi yang sedang aktif dan menyambungkannya ke port yang di-flash setelah proses selesai.

`firmware_example.ino` tetap dapat di-upload manual dari Arduino IDE. Untuk penggunaan manual,
ubah `SAMPLE_RATE_HZ`, `SERIAL_BAUD_RATE`, dan `TOUCH_PIN` sesuai eksperimen serta board.

**Penting:** tidak semua ESP32 memiliki peripheral touch yang sama. ESP32 klasik mendukung API `touchRead()` pada pin tertentu; varian seperti ESP32-S2/S3/C-series memiliki perbedaan dukungan dan API. Sesuaikan firmware dengan board.

## 3. Jalankan aplikasi

```bash
streamlit run app.py
```

Pilih port serial, tekan Connect, isi metadata, pasang material, Capture baseline, sentuh material, lalu Start touch recording. Tekan Stop & save untuk menyimpan.
Jumlah sampel touch recording dapat ditentukan di bagian Experiment setup. Recording akan berhenti dan tersimpan otomatis setelah batas sampel itu tercapai; tombol Stop & save tetap dapat digunakan untuk mengakhiri lebih awal.

## 4. Kelola dan sajikan data tersimpan

Aplikasi dashboard terpisah dapat dijalankan tanpa menghubungkan ESP32:

```bash
streamlit run manage_app.py
```

Dashboard membaca folder di `data/experiments` dan menyediakan filter serta ringkasan eksperimen. Plot rekaman menampilkan `raw_value` dan `baseline`, sedangkan diagram batang membandingkan rata-rata `delta_percent` per eksperimen. Untuk eksperimen yang dipilih, dashboard juga menampilkan rata-rata sampel `raw_value`, `baseline`, `delta`, dan `delta_percent`.

Metadata eksperimen dapat diedit di tab Manajemen. Data satu eksperimen atau semua eksperimen terfilter dapat diunduh sebagai JSON. Penghapusan folder eksperimen tersedia di tab Manajemen dan memerlukan konfirmasi.

Untuk menyajikan data lewat HTTP JSON API, jalankan di terminal lain:

```bash
python serve_json.py
```

Secara default API hanya bind ke komputer lokal pada port 8765:

- `GET /api/health` — status server.
- `GET /api/experiments` — daftar eksperimen, metadata, dan jumlah sampel.
- `GET /api/experiments/<nama-folder>` — metadata dan seluruh sampel dalam satu dokumen JSON.
- `GET /api/experiments/<nama-folder>/metadata` — metadata saja.

Untuk akses dari jaringan lokal, jalankan `python serve_json.py --host 0.0.0.0`. Anda juga dapat mengganti port (`--port`) atau direktori data (`--data-dir`).

## 5. Definisi pengukuran

Baseline dihitung sebagai rata-rata pembacaan saat material sudah berada di atas elektroda dan belum disentuh.

`delta = raw_value - baseline`

Persentase perubahan disimpan sebagai nilai absolut relatif terhadap baseline. Kolom delta bertanda tetap disimpan agar arah perubahan tidak hilang.

## 6. Catatan eksperimen

- Jaga posisi, luas, tekanan penempatan material, dan posisi sentuhan tetap konsisten.
- Lakukan beberapa trial untuk setiap kombinasi material-ketebalan.
- Simpan data mentah; jangan hanya menyimpan nilai rata-rata.
- Laju sampling firmware menggunakan interval berbasis `micros()` dan melewati tick yang terlewat.
  Laju aktual tetap bergantung pada waktu pembacaan touch dan kapasitas serial.
- Pembaca serial berjalan terus di latar belakang. Timestamp CSV dicatat saat satu baris sampel selesai diterima, sehingga tidak mengikuti waktu rerun atau refresh UI.
- Untuk eksperimen yang lebih kuat, catat juga kondisi tanpa material sebagai pengukuran kontrol terpisah, bukan menggantikan baseline utama.
