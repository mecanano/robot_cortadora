#include "Sensores.h"
#include <math.h>

bool Sensores::init(bool usarMPU, bool usarUltrasonico) {
  if (usarUltrasonico) ultra.init(TRIG_PIN, ECHO_PIN, DIST_MAX_CM);
  iniciado = usarUltrasonico;
  calibradoMPU = false;
  mpuListo = usarMPU && mpu.init();
  return !usarMPU || mpuListo;
}

void Sensores::actualizar() {
  if (iniciado) ultra.actualizar();
}

int Sensores::medirDistancia() {
  return distanciaValida() ? ultra.getDistancia() : -1;
}

bool Sensores::distanciaValida() const {
  return iniciado && ultra.ultimaLecturaValida();
}

bool Sensores::calibrarMPU() {
  if (!mpuListo) return false;
  calibradoMPU = mpu.calibrar();
  if (!calibradoMPU) mpuListo = false;
  return calibradoMPU;
}

bool Sensores::iniciarMPU() {
  calibradoMPU = false;
  mpuListo = mpu.init();
  return mpuListo;
}

bool Sensores::leerMPU(float &ax, float &ay, float &az,
                       float &gx, float &gy, float &gz) {
  if (!mpuListo) {
    ax = ay = az = gx = gy = gz = NAN;
    return false;
  }
  if (!mpu.leer(ax, ay, az, gx, gy, gz)) {
    mpuListo = false;
    calibradoMPU = false;
    ax = ay = az = gx = gy = gz = NAN;
    return false;
  }
  return true;
}

// Tabla de cuadratura x4: cada cambio valido cuenta +1 o -1.
// Un salto simultaneo de A y B se registra como transicion invalida.
void Sensores::contarEncoder(EstadoEncoder &encoder, int pinA, int pinB) {
  portENTER_CRITICAL_ISR(&muxEncoders);
  uint8_t nuevo = (digitalRead(pinA) << 1) | digitalRead(pinB);
  uint8_t anterior = encoder.anterior;
  int8_t paso = 0;
  switch ((anterior << 2) | nuevo) {
    case 1: case 7: case 8: case 14: paso = 1; break;
    case 2: case 4: case 11: case 13: paso = -1; break;
    default: break;
  }
  if (paso != 0) encoder.cuentas = encoder.cuentas + paso;
  else if (anterior != nuevo) encoder.invalidas = encoder.invalidas + 1;
  encoder.anterior = nuevo;
  portEXIT_CRITICAL_ISR(&muxEncoders);
}

void Sensores::interrupcionIzq(void *contexto) {
  auto *sensores = static_cast<Sensores *>(contexto);
  sensores->contarEncoder(sensores->encoderIzq, ENC_IZQ_A, ENC_IZQ_B);
}

void Sensores::interrupcionDer(void *contexto) {
  auto *sensores = static_cast<Sensores *>(contexto);
  sensores->contarEncoder(sensores->encoderDer, ENC_DER_A, ENC_DER_B);
}

void Sensores::iniciarEncoders(bool usarPullup) {
  if (encodersListos) return; // Repetir inicio no borra las cuentas.
  pinMode(ENC_IZQ_A, usarPullup ? INPUT_PULLUP : INPUT);
  pinMode(ENC_IZQ_B, usarPullup ? INPUT_PULLUP : INPUT);
  pinMode(ENC_DER_A, usarPullup ? INPUT_PULLUP : INPUT);
  pinMode(ENC_DER_B, usarPullup ? INPUT_PULLUP : INPUT);
  // Inicializar con las ruedas quietas para no perder transiciones al conectar ISR.
  encoderIzq.anterior = (digitalRead(ENC_IZQ_A) << 1) | digitalRead(ENC_IZQ_B);
  encoderDer.anterior = (digitalRead(ENC_DER_A) << 1) | digitalRead(ENC_DER_B);
  attachInterruptArg(digitalPinToInterrupt(ENC_IZQ_A), interrupcionIzq, this, CHANGE);
  attachInterruptArg(digitalPinToInterrupt(ENC_IZQ_B), interrupcionIzq, this, CHANGE);
  attachInterruptArg(digitalPinToInterrupt(ENC_DER_A), interrupcionDer, this, CHANGE);
  attachInterruptArg(digitalPinToInterrupt(ENC_DER_B), interrupcionDer, this, CHANGE);
  encodersListos = true;
}

bool Sensores::leerEncoders(long &izq, long &der,
                            unsigned long &invI, unsigned long &invD) {
  portENTER_CRITICAL(&muxEncoders);
  izq = encoderIzq.cuentas;
  der = encoderDer.cuentas;
  invI = encoderIzq.invalidas;
  invD = encoderDer.invalidas;
  portEXIT_CRITICAL(&muxEncoders);
  return encodersListos;
}

void Sensores::reiniciarEncoders() {
  portENTER_CRITICAL(&muxEncoders);
  encoderIzq.cuentas = 0;
  encoderDer.cuentas = 0;
  encoderIzq.invalidas = 0;
  encoderDer.invalidas = 0;
  // Se conserva el estado A/B: el reset no inventa un paso.
  portEXIT_CRITICAL(&muxEncoders);
}
