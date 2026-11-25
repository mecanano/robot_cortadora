#ifndef ULTRASONICO_H
#define ULTRASONICO_H

#include <Arduino.h>

// HC-SR04 sin librerias externas (NewPing no es del todo compatible con ESP32)
class Ultrasonico {
  public:
    struct Diagnostico {
      unsigned long pulsoUs = 0;
      int echoAntes = LOW;
      int echoDespues = LOW;
      const char *estado = "SIN_MEDIR";
    };
    Ultrasonico();
    void init(int trig, int echo, int maxDist);
    void actualizar();     // llamar en cada vuelta del loop
    int getDistancia();    // cm filtrada; consultar ultimaLecturaValida antes de usar
    bool ultimaLecturaValida() const { return lecturaValida; }
    Diagnostico getDiagnostico() const { return diagnostico; }

  private:
    int pinTrig, pinEcho;
    int distMax;
    int distancia;
    bool lecturaValida = false;
    Diagnostico diagnostico;
    int historial[3];
    unsigned long ultimoUpdate;
    static const unsigned long INTERVALO_MS = 60;
    int medir();
};

#endif
