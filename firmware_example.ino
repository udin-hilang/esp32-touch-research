// Contoh minimal untuk board ESP32 yang mendukung touchRead().
// Sesuaikan TOUCH_PIN dengan pin touch yang tersedia pada board Anda.
#define TOUCH_PIN T0
#define SAMPLE_RATE_HZ 10
#define SERIAL_BAUD_RATE 115200

#if SAMPLE_RATE_HZ < 1 || SAMPLE_RATE_HZ > 1000
#error "SAMPLE_RATE_HZ harus antara 1 dan 1000"
#endif

constexpr uint32_t SAMPLE_INTERVAL_US = 1000000UL / SAMPLE_RATE_HZ;
uint32_t nextSampleUs = 0;

void setup() {
  Serial.begin(SERIAL_BAUD_RATE);
  delay(500);
  nextSampleUs = micros();
}

void loop() {
  uint32_t nowUs = micros();
  if (static_cast<int32_t>(nowUs - nextSampleUs) >= 0) {
    int value = touchRead(TOUCH_PIN);
    Serial.println(value);  // Python membaca satu angka per baris.

    nextSampleUs += SAMPLE_INTERVAL_US;
    // Lewati tick yang terlewat agar pembacaan tidak mengejar jadwal lama.
    nowUs = micros();
    if (static_cast<int32_t>(nowUs - nextSampleUs) >= 0) {
      nextSampleUs = nowUs + SAMPLE_INTERVAL_US;
    }
  }
}
