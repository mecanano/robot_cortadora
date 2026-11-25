#ifndef BLUETOOTH_H
#define BLUETOOTH_H

#include <Arduino.h>
#include "Config.h"

// HC-05 conectado a Serial1 (pines BT_RX / BT_TX).
// Los datos tambien salen por Serial (USB) para verlos en la PC.
// Nota: el ESP32-S3 no tiene Bluetooth clasico propio, solo BLE;
// por eso se sigue usando el HC-05.
class Bluetooth {
  public:
    void init(long baudios = BT_BAUDIOS);
    void enviarDatos(float dist, float ax, float ay, float az,
                     float gx, float gy, float gz);
};

#endif
