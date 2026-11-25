#include "MotorControl.h"

MotorControl::MotorControl() {
  velBase = VELOCIDAD_BASE;
}

void MotorControl::init() {
#if DRIVER_MOTORES == 1
  if (DER_A < 0 || DER_B < 0 || PWM_D < 0 || IZQ_A < 0 || IZQ_B < 0 || PWM_I < 0) return;
  pinMode(DER_A, OUTPUT);  pinMode(DER_B, OUTPUT);  pinMode(PWM_D, OUTPUT);
  pinMode(IZQ_A, OUTPUT);  pinMode(IZQ_B, OUTPUT);  pinMode(PWM_I, OUTPUT);
#else
  if (D_RPWM < 0 || D_LPWM < 0 || I_RPWM < 0 || I_LPWM < 0) return;
  pinMode(D_RPWM, OUTPUT); pinMode(D_LPWM, OUTPUT);
  pinMode(I_RPWM, OUTPUT); pinMode(I_LPWM, OUTPUT);
#endif
  detener();
}

void MotorControl::setVelocidad(int v) {
  velBase = constrain(v, 0, 255);
}

// Maneja un motor. En L298N: pinA/pinB = sentido, pinPWM = velocidad.
// En IBT-2: pinA = RPWM, pinB = LPWM (pinPWM no se usa).
void MotorControl::motor(int pinA, int pinB, int pinPWM, int vel) {
  if (pinA < 0 || pinB < 0) return;
#if DRIVER_MOTORES == 1
  if (pinPWM < 0) return;
#endif
  vel = constrain(vel, -255, 255);
#if DRIVER_MOTORES == 1
  digitalWrite(pinA, vel > 0 ? HIGH : LOW);
  digitalWrite(pinB, vel < 0 ? HIGH : LOW);
  analogWrite(pinPWM, abs(vel));
#else
  (void)pinPWM;
  analogWrite(pinA, vel > 0 ? vel : 0);
  analogWrite(pinB, vel < 0 ? -vel : 0);
#endif
}

void MotorControl::setMotores(int velD, int velI) {
#if DRIVER_MOTORES == 1
  motor(DER_A, DER_B, PWM_D, velD);
  motor(IZQ_A, IZQ_B, PWM_I, velI);
#else
  motor(D_RPWM, D_LPWM, -1, velD);
  motor(I_RPWM, I_LPWM, -1, velI);
#endif
}

void MotorControl::avanzar()        { setMotores( velBase,  velBase); }
void MotorControl::retroceder()     { setMotores(-velBase, -velBase); }
void MotorControl::girarDerecha()   { setMotores(-velBase,  velBase); }
void MotorControl::girarIzquierda() { setMotores( velBase, -velBase); }
void MotorControl::detener()        { setMotores(0, 0); }
