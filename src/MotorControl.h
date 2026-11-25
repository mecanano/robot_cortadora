#ifndef MOTORCONTROL_H
#define MOTORCONTROL_H

#include <Arduino.h>
#include "Config.h"

class MotorControl {
  public:
    MotorControl();
    void init();
    void setVelocidad(int v);

    void avanzar();
    void retroceder();
    void girarDerecha();
    void girarIzquierda();
    void detener();

    // Control fino (para el PID): -255 a 255, el signo indica el sentido
    void setMotores(int velD, int velI);

  private:
    int velBase;
    void motor(int pinA, int pinB, int pinPWM, int vel);
};

#endif
