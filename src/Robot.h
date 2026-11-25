#ifndef ROBOT_H
#define ROBOT_H

#include "Config.h"
#include "MotorControl.h"
#include "Sensores.h"
#include "Bluetooth.h"

class Robot {
  public:
    MotorControl motor;
    Sensores sensor;
    Bluetooth bt;

    void init();
    void loopPrincipal();
    void evadirObstaculo();
};

#endif
