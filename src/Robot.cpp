#include "Robot.h"

void Robot::init() {
  Serial.begin(115200);     // USB, para ver mensajes en la PC
  delay(500);
  bt.init();
  motor.init();

  if (!sensor.init()) {
    Serial.println("ERROR: no se encontro el MPU6050 (revisar cables en I2C_SDA / I2C_SCL)");
  }

  if (sensor.mpuDisponible()) {
    Serial.println("Calibrando MPU, no mover el robot...");
    sensor.calibrarMPU();
  }
  Serial.println("Robot listo");
}

void Robot::evadirObstaculo() {
  motor.detener();
  delay(300);

  motor.retroceder();
  delay(700);

  motor.girarDerecha();
  delay(600);

  motor.detener();
  delay(200);
}

void Robot::loopPrincipal() {
  sensor.actualizar();
  int dist = sensor.medirDistancia();

  float ax, ay, az, gx, gy, gz;
  sensor.leerMPU(ax, ay, az, gx, gy, gz);

  // ---- Envio por Bluetooth ----
  bt.enviarDatos(dist, ax, ay, az, gx, gy, gz);

  // ---- Logica del robot ----
  if (!sensor.distanciaValida()) {
    motor.detener();
  } else if (dist < UMBRAL_OBS_CM) {
    evadirObstaculo();
  } else {
    motor.avanzar();
  }

  delay(200);
}
