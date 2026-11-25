#ifndef SENSORES_H
#define SENSORES_H

#include <Arduino.h>
#include "Config.h"
#include "Ultrasonico.h"
#include "MPU.h"

// Agrupa todos los sensores del robot
class Sensores {
  public:
    // Primer false omite MPU; segundo false omite tambien el ultrasonico.
    // Retorna false si se solicito MPU y no se encontro.
    bool init(bool usarMPU = true, bool usarUltrasonico = true);
    void actualizar();          // llamar en cada vuelta del loop
    int  medirDistancia();      // cm filtrados; -1 si la lectura no es valida
    bool distanciaValida() const;
    Ultrasonico::Diagnostico diagnosticoUltrasonico() const { return ultra.getDiagnostico(); }
    bool mpuDisponible() const { return mpuListo; }
    bool iniciarMPU();
    bool mpuCalibrado() const { return calibradoMPU; }
    bool calibrarMPU();         // false si el MPU no se inicializo
    bool leerMPU(float &ax, float &ay, float &az,
                 float &gx, float &gy, float &gz);
    // Conteo x4 de A/B; no calcula RPM sin conocer cuentas por vuelta.
    void iniciarEncoders(bool usarPullup = true);
    bool leerEncoders(long &izq, long &der, unsigned long &invI, unsigned long &invD);
    void reiniciarEncoders();
    // Indica configuracion de interrupciones, NO presencia fisica del encoder.
    bool encodersIniciados() const { return encodersListos; }

    // Las interrupciones mantienen una referencia a esta instancia.
    Sensores() = default;
    Sensores(const Sensores &) = delete;
    Sensores &operator=(const Sensores &) = delete;

  private:
    Ultrasonico ultra;
    MPU mpu;
    bool iniciado = false;
    bool mpuListo = false;
    bool calibradoMPU = false;
    struct EstadoEncoder {
      volatile long cuentas = 0;
      volatile unsigned long invalidas = 0;
      volatile uint8_t anterior = 0;
    } encoderIzq, encoderDer;
    portMUX_TYPE muxEncoders = portMUX_INITIALIZER_UNLOCKED;
    bool encodersListos = false;
    static void IRAM_ATTR interrupcionIzq(void *contexto);
    static void IRAM_ATTR interrupcionDer(void *contexto);
    void IRAM_ATTR contarEncoder(EstadoEncoder &encoder, int pinA, int pinB);
};

#endif
