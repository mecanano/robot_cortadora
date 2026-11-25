#include "Bluetooth.h"

void Bluetooth::init(long baudios) {
  if (BT_RX < 0 || BT_TX < 0) return;
  Serial1.begin(baudios, SERIAL_8N1, BT_RX, BT_TX);
}

void Bluetooth::enviarDatos(float dist, float ax, float ay, float az,
                            float gx, float gy, float gz) {
  char linea[128];
  snprintf(linea, sizeof(linea),
           "DIST: %.0f | ACC: %.2f,%.2f,%.2f | GYRO: %.1f,%.1f,%.1f",
           dist, ax, ay, az, gx, gy, gz);
  Serial.println(linea);    // USB
  if (BT_RX >= 0 && BT_TX >= 0) Serial1.println(linea);   // HC-05
}
