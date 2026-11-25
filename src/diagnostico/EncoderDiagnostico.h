#pragma once
#include <Arduino.h>
#include "../Config.h"

class EncoderDiagnostico {
public:
  struct Estadistica {
    long cuentas = 0;
    uint32_t positivos = 0, negativos = 0, invalidas = 0, sinCambio = 0;
    uint32_t cambios[2] = {}, subidas[2] = {}, bajadas[2] = {}, llamadas[2] = {};
    uint32_t estados[4] = {}, transiciones[16] = {};
    uint8_t ab = 0;
  };
  struct Evento {
    uint32_t us;
    uint8_t rueda, antes, ahora, origen;
    int8_t paso;
  };
  void iniciar(bool pullup);
  void reiniciar();
  void leer(Estadistica (&salida)[2], uint32_t &perdidos, uint8_t (&actual)[2]);
  bool siguiente(Evento &evento);
private:
  struct Contexto { EncoderDiagnostico *dueno; uint8_t canal; } contextos[4];
  Estadistica ruedas[2];
  static constexpr uint16_t CAPACIDAD = 256;
  Evento eventos[CAPACIDAD];
  uint16_t cabeza = 0, cola = 0;
  uint32_t descartados = 0;
  bool iniciado = false;
  portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
  static void IRAM_ATTR interrupcion(void *arg);
  void IRAM_ATTR capturar(uint8_t origen);
  static uint8_t IRAM_ATTR estado(uint32_t banco, uint8_t rueda);
};
