#pragma once
#include <cstdint>

struct HostGpio {
  struct {
    uint32_t val = 0;
  } in1;
};

inline HostGpio GPIO{};
