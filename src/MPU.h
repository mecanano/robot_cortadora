#ifndef MPU_H
#define MPU_H

#include <Arduino.h>
#include <Wire.h>
#include <MPU6050.h>

class MPU {
  public:
    MPU();
    bool init();          // devuelve false si no encuentra el sensor
    bool calibrar();      // false si falla una lectura I2C; robot quieto y horizontal
    // aceleracion en g, giro en grados/segundo
    bool leer(float &ax_r, float &ay_r, float &az_r,
              float &gx_r, float &gy_r, float &gz_r);

  private:
    MPU6050 sensor;
    int16_t ax, ay, az, gx, gy, gz;
    long ax_off, ay_off, az_off;
    long gx_off, gy_off, gz_off;
    bool leerRegistro(uint8_t registro, uint8_t *datos, size_t cantidad);
    bool leerCrudo();
};

#endif
