#include "MPU.h"
#include "Config.h"
#include <math.h>

// Escalas por defecto del MPU6050: +-2g y +-250 grados/s
static const float LSB_POR_G      = 16384.0;
static const float LSB_POR_GRADO  = 131.0;

MPU::MPU() : sensor(MPU_DIRECCION) {
  ax = ay = az = gx = gy = gz = 0;
  ax_off = ay_off = az_off = 0;
  gx_off = gy_off = gz_off = 0;
}

bool MPU::leerRegistro(uint8_t registro, uint8_t *datos, size_t cantidad) {
  Wire.beginTransmission(MPU_DIRECCION);
  Wire.write(registro);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(static_cast<uint8_t>(MPU_DIRECCION), cantidad, true) != cantidad)
    return false;
  for (size_t i = 0; i < cantidad; ++i) {
    if (!Wire.available()) return false;
    datos[i] = Wire.read();
  }
  return true;
}

bool MPU::leerCrudo() {
  uint8_t datos[14];
  if (!leerRegistro(0x3B, datos, sizeof(datos))) return false;
  auto valor = [&](int i) -> int16_t {
    return static_cast<int16_t>((static_cast<uint16_t>(datos[i]) << 8) | datos[i + 1]);
  };
  ax = valor(0); ay = valor(2); az = valor(4);
  gx = valor(8); gy = valor(10); gz = valor(12);
  return true;
}

bool MPU::init() {
  if (I2C_SDA < 0 || I2C_SCL < 0) return false;
  if (!Wire.begin(I2C_SDA, I2C_SCL)) return false;
  Wire.setClock(100000);
  Wire.setTimeOut(MPU_TIMEOUT_MS);
  uint8_t identidad;
  if (!leerRegistro(0x75, &identidad, 1) || (identidad & 0x7E) != 0x68) return false;
  sensor.initialize();
  // Comprobar rangos escritos: +-2g y +-250 grados/s.
  uint8_t rangoGyro, rangoAccel;
  if (!leerRegistro(0x1B, &rangoGyro, 1) || !leerRegistro(0x1C, &rangoAccel, 1)) return false;
  if ((rangoGyro & 0x18) != 0 || (rangoAccel & 0x18) != 0) return false;
  return leerCrudo();
}

bool MPU::calibrar() {
  long ax_s = 0, ay_s = 0, az_s = 0;
  long gx_s = 0, gy_s = 0, gz_s = 0;

  for (int i = 0; i < MPU_MUESTRAS_CALIBRACION; i++) {
    if (!leerCrudo()) return false;
    // Rechazar giro durante calibracion; no garantiza ausencia de vibracion lenta.
    if (fabsf(gx / LSB_POR_GRADO) > 5.0f || fabsf(gy / LSB_POR_GRADO) > 5.0f ||
        fabsf(gz / LSB_POR_GRADO) > 5.0f) return false;
    ax_s += ax; ay_s += ay; az_s += az;
    gx_s += gx; gy_s += gy; gz_s += gz;
    delay(2);
  }

  ax_off = ax_s / MPU_MUESTRAS_CALIBRACION;
  ay_off = ay_s / MPU_MUESTRAS_CALIBRACION;
  // En reposo Z mide 1 g (la gravedad): no hay que restarla,
  // si no se pierde la referencia para detectar pendientes.
  az_off = az_s / MPU_MUESTRAS_CALIBRACION - (long)LSB_POR_G;
  gx_off = gx_s / MPU_MUESTRAS_CALIBRACION;
  gy_off = gy_s / MPU_MUESTRAS_CALIBRACION;
  gz_off = gz_s / MPU_MUESTRAS_CALIBRACION;
  return true;
}

bool MPU::leer(float &ax_r, float &ay_r, float &az_r,
               float &gx_r, float &gy_r, float &gz_r) {
  if (!leerCrudo()) {
    ax_r = ay_r = az_r = gx_r = gy_r = gz_r = NAN;
    return false;
  }

  ax_r = (ax - ax_off) / LSB_POR_G;
  ay_r = (ay - ay_off) / LSB_POR_G;
  az_r = (az - az_off) / LSB_POR_G;
  gx_r = (gx - gx_off) / LSB_POR_GRADO;
  gy_r = (gy - gy_off) / LSB_POR_GRADO;
  gz_r = (gz - gz_off) / LSB_POR_GRADO;
  return true;
}
