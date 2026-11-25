#pragma once
#include <stdint.h>

// Convencion relativa: 00 -> 01 -> 11 -> 10 -> 00 es positivo.
// No significa "adelante" hasta cotejarlo con el movimiento fisico.
inline __attribute__((always_inline)) int8_t pasoCuadratura(uint8_t antes, uint8_t ahora) {
  switch ((antes << 2) | ahora) {
    case 1: case 7: case 8: case 14: return 1;
    case 2: case 4: case 11: case 13: return -1;
    default: return 0;
  }
}
