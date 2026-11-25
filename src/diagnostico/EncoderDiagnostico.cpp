#include "EncoderDiagnostico.h"
#include "Cuadratura.h"
#include "soc/gpio_struct.h"

static_assert(ENC_IZQ_A >= 32 && ENC_IZQ_A <= 48 && ENC_IZQ_B >= 32 && ENC_IZQ_B <= 48 &&
              ENC_DER_A >= 32 && ENC_DER_A <= 48 && ENC_DER_B >= 32 && ENC_DER_B <= 48,
              "Captura simultanea implementada para GPIO32..48; no cambiar pines sin revisar");

uint8_t EncoderDiagnostico::estado(uint32_t banco, uint8_t rueda) {
  if (rueda == 0)
    return (((banco >> (ENC_IZQ_A - 32)) & 1U) << 1) | ((banco >> (ENC_IZQ_B - 32)) & 1U);
  return (((banco >> (ENC_DER_A - 32)) & 1U) << 1) | ((banco >> (ENC_DER_B - 32)) & 1U);
}

void EncoderDiagnostico::interrupcion(void *arg) {
  auto *ctx = static_cast<Contexto *>(arg);
  ctx->dueno->capturar(ctx->canal);
}

void EncoderDiagnostico::capturar(uint8_t origen) {
  portENTER_CRITICAL_ISR(&mux);
  // Un solo acceso para los CUATRO canales; evita leer A y B en instantes distintos.
  const uint32_t banco = GPIO.in1.val;
  const uint32_t us = micros();
  ruedas[origen / 2].llamadas[origen % 2]++;
  for (uint8_t lado = 0; lado < 2; ++lado) {
    auto &r = ruedas[lado];
    const uint8_t nuevo = estado(banco, lado), previo = r.ab;
    if (previo == nuevo) {
      if (lado == origen / 2) r.sinCambio++;
      continue;
    }
    const uint8_t cambio = previo ^ nuevo;
    for (uint8_t canal = 0; canal < 2; ++canal) {
      const uint8_t mascara = canal == 0 ? 2 : 1;
      if (cambio & mascara) {
        r.cambios[canal]++;
        if (nuevo & mascara) r.subidas[canal]++;
        else r.bajadas[canal]++;
      }
    }
    const int8_t paso = pasoCuadratura(previo, nuevo);
    if (cambio == 3) r.invalidas++;
    else if (paso > 0) r.positivos++;
    else if (paso < 0) r.negativos++;
    r.cuentas += paso;
    r.estados[nuevo]++;
    r.transiciones[(previo << 2) | nuevo]++;
    r.ab = nuevo;
    const uint16_t siguiente = (cabeza + 1) % CAPACIDAD;
    if (siguiente == cola) descartados++;
    else {
      eventos[cabeza] = {us, lado, previo, nuevo, origen, paso};
      cabeza = siguiente;
    }
  }
  portEXIT_CRITICAL_ISR(&mux);
}

void EncoderDiagnostico::iniciar(bool pullup) {
  const int pines[] = {ENC_IZQ_A, ENC_IZQ_B, ENC_DER_A, ENC_DER_B};
  if (iniciado) for (int pin : pines) detachInterrupt(digitalPinToInterrupt(pin));
  for (int pin : pines) pinMode(pin, pullup ? INPUT_PULLUP : INPUT);
  reiniciar(); // Ruedas quietas: la reinstalacion deja una ventana sin captura.
  for (uint8_t i = 0; i < 4; ++i) {
    contextos[i] = {this, i};
    attachInterruptArg(digitalPinToInterrupt(pines[i]), interrupcion, &contextos[i], CHANGE);
  }
  iniciado = true;
}

void EncoderDiagnostico::reiniciar() {
  portENTER_CRITICAL(&mux);
  const uint32_t banco = GPIO.in1.val;
  for (uint8_t i = 0; i < 2; ++i) {
    ruedas[i] = Estadistica{};
    ruedas[i].ab = estado(banco, i);
  }
  cabeza = cola = 0; descartados = 0;
  portEXIT_CRITICAL(&mux);
}

void EncoderDiagnostico::leer(Estadistica (&salida)[2], uint32_t &perdidos, uint8_t (&actual)[2]) {
  portENTER_CRITICAL(&mux);
  const uint32_t banco = GPIO.in1.val;
  for (uint8_t i = 0; i < 2; ++i) { salida[i] = ruedas[i]; actual[i] = estado(banco, i); }
  perdidos = descartados;
  portEXIT_CRITICAL(&mux);
}

bool EncoderDiagnostico::siguiente(Evento &evento) {
  bool disponible = false;
  portENTER_CRITICAL(&mux);
  if (cola != cabeza) { evento = eventos[cola]; cola = (cola + 1) % CAPACIDAD; disponible = true; }
  portEXIT_CRITICAL(&mux);
  return disponible;
}
