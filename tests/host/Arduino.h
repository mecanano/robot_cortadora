#pragma once
#include <array>
#include <cassert>
#include <cstdint>

#define IRAM_ATTR
struct portMUX_TYPE {};
#define portMUX_INITIALIZER_UNLOCKED {}
inline void portENTER_CRITICAL(portMUX_TYPE*) {}
inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
inline void portENTER_CRITICAL_ISR(portMUX_TYPE*) {}
inline void portEXIT_CRITICAL_ISR(portMUX_TYPE*) {}

inline constexpr int INPUT = 0, INPUT_PULLUP = 2, CHANGE = 3;

namespace host {
struct Interrupt {
  void (*callback)(void*) = nullptr;
  void* context = nullptr;
};

inline std::array<Interrupt, 49> interrupts{};
inline std::array<int, 49> modes{};
inline uint32_t clockUs = 0;

inline void fire(int pin) {
  const auto registered = interrupts.at(pin);
  assert(registered.callback);
  registered.callback(registered.context);
}
}

inline uint32_t micros() { return host::clockUs; }
inline int digitalPinToInterrupt(int pin) { return pin; }
inline void pinMode(int pin, int mode) { host::modes.at(pin) = mode; }
inline void detachInterrupt(int pin) { host::interrupts.at(pin) = {}; }
inline void attachInterruptArg(int pin, void (*callback)(void*), void* context, int mode) {
  assert(mode == CHANGE);
  assert(!host::interrupts.at(pin).callback);
  host::interrupts.at(pin) = {callback, context};
}
