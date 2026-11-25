#include "Ultrasonico.h"

Ultrasonico::Ultrasonico() {
  pinTrig = pinEcho = -1;
  distMax = 0;
  distancia = -1;
  ultimoUpdate = 0;
  historial[0] = historial[1] = historial[2] = 0;
}

void Ultrasonico::init(int trig, int echo, int maxDist) {
  pinTrig = trig;
  pinEcho = echo;
  distMax = maxDist;
  lecturaValida = false;
  diagnostico = Diagnostico{};
  ultimoUpdate = millis();
  pinMode(pinTrig, OUTPUT);
  pinMode(pinEcho, INPUT);
  digitalWrite(pinTrig, LOW);
  historial[0] = historial[1] = historial[2] = maxDist;
  distancia = maxDist;
}

// Una medicion en cm. El sonido tarda ~58 us por cada cm (ida y vuelta).
int Ultrasonico::medir() {
  digitalWrite(pinTrig, LOW);
  delayMicroseconds(2);
  diagnostico.echoAntes = digitalRead(pinEcho);
  digitalWrite(pinTrig, HIGH);
  delayMicroseconds(10);
  digitalWrite(pinTrig, LOW);

  unsigned long timeout = (unsigned long)distMax * 58UL + 1000UL;
  unsigned long dur = pulseIn(pinEcho, HIGH, timeout);
  diagnostico.pulsoUs = dur;
  diagnostico.echoDespues = digitalRead(pinEcho);
  if (dur == 0) {
    // El timeout no distingue sensor desconectado de pulso ausente/incompleto.
    diagnostico.estado = diagnostico.echoDespues == HIGH ?
        "TIMEOUT_ECHO_ALTO" : "TIMEOUT_SIN_PULSO_COMPLETO";
    return -1;
  }
  int cm = (int)(dur / 58UL);
  if (cm < 2 || cm > distMax) {
    diagnostico.estado = "PULSO_FUERA_DE_RANGO";
    return -1;
  }
  diagnostico.estado = "LECTURA_VALIDA";
  return cm;
}

static int mediana3(int a, int b, int c) {
  if ((a <= b && b <= c) || (c <= b && b <= a)) return b;
  if ((b <= a && a <= c) || (c <= a && a <= b)) return a;
  return c;
}

void Ultrasonico::actualizar() {
  if (pinTrig < 0) return;
  if (millis() - ultimoUpdate < INTERVALO_MS) return;
  ultimoUpdate = millis();

  int nueva = medir();
  if (nueva < 0) {
    lecturaValida = false;
    distancia = distMax;  // Compatibilidad con los consumidores anteriores.
    return;
  }
  if (!lecturaValida) historial[0] = historial[1] = historial[2] = nueva;
  lecturaValida = true;
  historial[0] = historial[1];
  historial[1] = historial[2];
  historial[2] = nueva;
  distancia = mediana3(historial[0], historial[1], historial[2]);
}

int Ultrasonico::getDistancia() {
  return distancia;
}
