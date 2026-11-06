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

## 4. Definisi pengukuran

Baseline dihitung sebagai rata-rata pembacaan saat material sudah berada di atas elektroda dan belum disentuh.

`delta = raw_value - baseline`

Persentase perubahan disimpan sebagai nilai absolut relatif terhadap baseline. Kolom delta bertanda tetap disimpan agar arah perubahan tidak hilang.

## 5. Catatan eksperimen

- Jaga posisi, luas, tekanan penempatan material, dan posisi sentuhan tetap konsisten.
- Lakukan beberapa trial untuk setiap kombinasi material-ketebalan.
- Simpan data mentah; jangan hanya menyimpan nilai rata-rata.
- Laju sampling firmware menggunakan interval berbasis `micros()` dan melewati tick yang terlewat.
  Laju aktual tetap bergantung pada waktu pembacaan touch dan kapasitas serial.
- Pembaca serial berjalan terus di latar belakang. Timestamp CSV dicatat saat satu baris sampel selesai diterima, sehingga tidak mengikuti waktu rerun atau refresh UI.
- Untuk eksperimen yang lebih kuat, catat juga kondisi tanpa material sebagai pengukuran kontrol terpisah, bukan menggantikan baseline utama.
