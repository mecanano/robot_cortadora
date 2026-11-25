#include "EncoderDiagnostico.h"
#include "Cuadratura.h"
#include "soc/gpio_struct.h"

#include <cstdlib>
#include <iostream>
#include <string_view>

namespace {
constexpr int pins[2][2] = {{ENC_IZQ_A, ENC_IZQ_B}, {ENC_DER_A, ENC_DER_B}};
constexpr uint8_t forward[] = {0, 1, 3, 2, 0};
constexpr uint8_t reverse[] = {0, 2, 3, 1, 0};

#define EXPECT(condition)                                                         \
  do {                                                                            \
    if (!(condition)) {                                                           \
      std::cerr << __FILE__ << ':' << __LINE__ << ": " << #condition << '\n';       \
      std::exit(EXIT_FAILURE);                                                     \
    }                                                                             \
  } while (false)

void setState(int wheel, uint8_t state) {
  for (int channel = 0; channel < 2; ++channel) {
    const uint32_t bit = 1U << (pins[wheel][channel] - 32);
    GPIO.in1.val &= ~bit;
    if (state & (2U >> channel)) GPIO.in1.val |= bit;
  }
}

void edge(int wheel, uint8_t state, int sourceChannel) {
  setState(wheel, state);
  host::clockUs += 10;
  host::fire(pins[wheel][sourceChannel]);
}

struct Snapshot {
  EncoderDiagnostico::Estadistica wheel[2];
  uint32_t dropped;
  uint8_t actual[2];

  explicit Snapshot(EncoderDiagnostico& encoder) {
    encoder.leer(wheel, dropped, actual);
  }
};

void checkClear(const EncoderDiagnostico::Estadistica& wheel, uint8_t state) {
  EXPECT(wheel.ab == state);
  EXPECT(wheel.cuentas == 0 && wheel.positivos == 0 && wheel.negativos == 0);
  EXPECT(wheel.invalidas == 0 && wheel.sinCambio == 0);
  for (int channel = 0; channel < 2; ++channel) {
    EXPECT(wheel.cambios[channel] == 0 && wheel.llamadas[channel] == 0);
    EXPECT(wheel.subidas[channel] == 0 && wheel.bajadas[channel] == 0);
  }
  for (auto count : wheel.estados) EXPECT(count == 0);
  for (auto count : wheel.transiciones) EXPECT(count == 0);
}

void checkTransitions(EncoderDiagnostico& encoder) {
  constexpr int expected[4][4] = {{0, 1, -1, 0}, {-1, 0, 0, 1},
                                  {1, 0, 0, -1}, {0, -1, 1, 0}};
  for (int wheel = 0; wheel < 2; ++wheel) {
    for (uint8_t before = 0; before < 4; ++before) {
      for (uint8_t after = 0; after < 4; ++after) {
        setState(wheel, before);
        setState(1 - wheel, 0);
        encoder.reiniciar();
        const uint8_t changed = before ^ after;
        const int source = changed == 1 ? 1 : 0;
        edge(wheel, after, source);

        const Snapshot capture(encoder);
        const auto& stats = capture.wheel[wheel];
        const int step = expected[before][after];
        EXPECT(pasoCuadratura(before, after) == step);
        EXPECT(stats.cuentas == step && stats.ab == after && capture.actual[wheel] == after);
        EXPECT(stats.positivos == (step > 0) && stats.negativos == (step < 0));
        EXPECT(stats.invalidas == (changed == 3) && stats.sinCambio == (changed == 0));
        for (int i = 0; i < 4; ++i) EXPECT(stats.estados[i] == (changed && i == after));
        for (int i = 0; i < 16; ++i) {
          EXPECT(stats.transiciones[i] == (changed && i == ((before << 2) | after)));
        }
        for (int channel = 0; channel < 2; ++channel) {
          const unsigned mask = 2U >> channel;
          const bool flipped = changed & mask;
          EXPECT(stats.cambios[channel] == flipped);
          EXPECT(stats.subidas[channel] == (flipped && (after & mask)));
          EXPECT(stats.bajadas[channel] == (flipped && !(after & mask)));
          EXPECT(stats.llamadas[channel] == (channel == source));
        }
        checkClear(capture.wheel[1 - wheel], 0);
        EXPECT(capture.dropped == 0);
        EncoderDiagnostico::Evento event{};
        EXPECT(encoder.siguiente(event) == (changed != 0));
        if (changed) {
          EXPECT(event.us == host::clockUs && event.rueda == wheel);
          EXPECT(event.antes == before && event.ahora == after);
          EXPECT(event.origen == wheel * 2 + source && event.paso == step);
        }
        EXPECT(!encoder.siguiente(event));
      }
    }
  }
}

void checkCycle(EncoderDiagnostico& encoder, int wheel, const uint8_t (&sequence)[5],
                int expected) {
  setState(0, 0);
  setState(1, 0);
  encoder.reiniciar();
  for (int i = 1; i < 5; ++i) {
    edge(wheel, sequence[i], (sequence[i] ^ sequence[i - 1]) == 2 ? 0 : 1);
  }
  const Snapshot capture(encoder);
  const auto& stats = capture.wheel[wheel];
  EXPECT(stats.cuentas == expected);
  EXPECT(stats.positivos == (expected > 0 ? 4U : 0U));
  EXPECT(stats.negativos == (expected < 0 ? 4U : 0U) && stats.invalidas == 0);
  for (int channel = 0; channel < 2; ++channel) {
    EXPECT(stats.subidas[channel] == 1 && stats.bajadas[channel] == 1);
  }
  checkClear(capture.wheel[1 - wheel], 0);
}

void checkReset(EncoderDiagnostico& encoder) {
  for (uint8_t ab = 0; ab < 4; ++ab) {
    setState(0, ab);
    setState(1, ab);
    encoder.reiniciar();
    const Snapshot capture(encoder);
    for (int wheel = 0; wheel < 2; ++wheel) {
      checkClear(capture.wheel[wheel], ab);
      EXPECT(capture.actual[wheel] == ab);
      host::fire(pins[wheel][0]);
    }
    const Snapshot repeated(encoder);
    for (const auto& stats : repeated.wheel) {
      EXPECT(stats.cuentas == 0 && stats.invalidas == 0 && stats.sinCambio == 1);
    }
    EncoderDiagnostico::Evento event{};
    EXPECT(capture.dropped == 0 && !encoder.siguiente(event));
  }
}

void checkSharedSnapshot(EncoderDiagnostico& encoder) {
  setState(0, 0);
  setState(1, 0);
  encoder.reiniciar();
  setState(1, 2);
  edge(0, 1, 1);
  const Snapshot capture(encoder);
  EXPECT(capture.wheel[0].cuentas == 1 && capture.wheel[1].cuentas == -1);
  EXPECT(capture.wheel[0].llamadas[1] == 1 && capture.wheel[1].llamadas[0] == 0);
  for (int wheel = 0; wheel < 2; ++wheel) {
    EncoderDiagnostico::Evento event{};
    EXPECT(encoder.siguiente(event));
    EXPECT(event.us == host::clockUs && event.origen == 1 && event.rueda == wheel);
  }
}

void checkQueue(EncoderDiagnostico& encoder) {
  constexpr unsigned retained = 255;
  constexpr unsigned injected = 300;
  setState(0, 0);
  setState(1, 0);
  encoder.reiniciar();
  const uint32_t start = host::clockUs;
  for (unsigned i = 1; i <= injected; ++i) {
    edge(0, forward[i % 4], i % 2);
  }
  const Snapshot capture(encoder);
  EXPECT(capture.dropped == injected - retained);
  EXPECT(capture.wheel[0].cuentas == injected && capture.wheel[0].positivos == injected);
  EncoderDiagnostico::Evento event{};
  for (unsigned i = 1; i <= retained; ++i) {
    EXPECT(encoder.siguiente(event));
    EXPECT(event.us == start + i * 10 && event.rueda == 0 && event.paso == 1);
    EXPECT(event.antes == forward[(i - 1) % 4] && event.ahora == forward[i % 4]);
  }
  EXPECT(!encoder.siguiente(event));
  edge(0, 1, 1);
  EXPECT(encoder.siguiente(event) && event.us == host::clockUs && event.ahora == 1);
  EXPECT(!encoder.siguiente(event));
  encoder.reiniciar();
  const Snapshot reset(encoder);
  EXPECT(reset.dropped == 0 && !encoder.siguiente(event));
  checkClear(reset.wheel[0], 1);
  checkClear(reset.wheel[1], 0);
}
}

int main(int argc, char** argv) {
  const bool negativeControl = argc == 2 && std::string_view(argv[1]) == "--expect-failure";
  EncoderDiagnostico encoder;
  encoder.iniciar(true);
  for (const auto& wheel : pins) {
    for (int pin : wheel) EXPECT(host::modes.at(pin) == INPUT_PULLUP);
  }
  encoder.iniciar(false);
  for (const auto& wheel : pins) {
    for (int pin : wheel) EXPECT(host::modes.at(pin) == INPUT);
  }

  checkCycle(encoder, 0, forward, negativeControl ? 5 : 4);
  checkCycle(encoder, 1, forward, 4);
  checkCycle(encoder, 0, reverse, -4);
  checkCycle(encoder, 1, reverse, -4);
  checkTransitions(encoder);
  checkReset(encoder);
  checkSharedSnapshot(encoder);
  checkQueue(encoder);
  std::cout << "OK: 16 transiciones por rueda, ciclos, flancos, reset y cola de eventos\n";
}
