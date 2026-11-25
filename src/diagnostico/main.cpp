#include <Arduino.h>
#include <math.h>
#include "esp_system.h"
#include "driver/gpio.h"
#include "EncoderDiagnostico.h"
#include "../MPU.h"
#include "../Ultrasonico.h"
#include "../MotorControl.h"

namespace {
constexpr int mapa[] = {ENC_IZQ_A, ENC_IZQ_B, ENC_DER_A, ENC_DER_B, I2C_SDA, I2C_SCL,
                       TRIG_PIN, ECHO_PIN, PWM_D, DER_A, DER_B, PWM_I, IZQ_A, IZQ_B,
                       RGB_LED_PIN, PIN_PROG};
constexpr bool pinExpuesto(int p) {
  return p == 0 || p == 1 || p == 2 || p == 3 || (p >= 15 && p <= 18) ||
         p == 21 || (p >= 38 && p <= 48);
}
constexpr bool mapaValido() {
  for (size_t i = 0; i < sizeof(mapa) / sizeof(mapa[0]); ++i) {
    if (!pinExpuesto(mapa[i])) return false;
    for (size_t j = 0; j < i; ++j) if (mapa[i] == mapa[j]) return false;
  }
  return PWM_D != 46 && DER_A != 46 && DER_B != 46 && PWM_I != 46 &&
         IZQ_A != 46 && IZQ_B != 46 && TRIG_PIN != 46;
}
static_assert(DRIVER_MOTORES == 1, "Diagnostico preparado para L298N");
static_assert(mapaValido(), "GPIO duplicado/no expuesto, memoria, USB o salida en GPIO46");
static_assert(PRUEBA_PWM > 0 && PRUEBA_PWM <= 255 && PRUEBA_PULSO_MS > 0 &&
              PRUEBA_PULSO_MS <= 3000, "Limites de banco: PWM1..255, pulso1..3000 ms");

EncoderDiagnostico encoder;
MPU mpu;
Ultrasonico ultra;
MotorControl motores;
enum class Modo { Encoder, MPU, Ultra };
Modo modo = Modo::Encoder;
bool pullup = true, traza = true, mpuListo = false, calibrado = false;
bool mpuValido = false, ultraIniciado = false, armado = false, moviendo = false;
bool confirmaEncoder = false, confirmaMPU = false, confirmaUltra = false;
bool usbAnterior = false;
uint32_t ultimoReporte = 0, ultimaLectura = 0, inicioMotor = 0, ultimaParada = 0, ultimoLoop = 0;
bool huboMotor = false;
uint32_t baselineError[2] = {}, baselinePasos[2] = {};
uint8_t ladoMotor = 0;
size_t capacidadSerial = 0;
uint32_t nUltra = 0, malasUltra = 0;
double mediaUltra = 0, m2Ultra = 0;
float minimoUltra = 0, maximoUltra = 0;

void parar(const char *motivo) {
  motores.detener();
  if (moviendo) { ultimaParada = millis(); huboMotor = true; }
  moviendo = false; armado = false;
  Serial.printf("noche PARADA: %s\n", motivo);
}

void ayuda() {
  Serial.println("\nnoche DIAG-S3-20261115-v1; sin navegacion, sin activacion automatica.");
  Serial.printf("noche buffer_TX_bytes=%u; si faltan lineas repetir con traza apagada\n", static_cast<unsigned>(capacidadSerial));
  Serial.printf("noche PINES: ENC I A/B=%d/%d D A/B=%d/%d | MPU SDA/SCL=%d/%d addr=0x%02X\n",
                ENC_IZQ_A, ENC_IZQ_B, ENC_DER_A, ENC_DER_B, I2C_SDA, I2C_SCL, MPU_DIRECCION);
  Serial.printf("noche L298: D ENA/IN1/IN2=%d/%d/%d | I ENB/IN3/IN4=%d/%d/%d | HC-SR04 frontal TRIG/ECHO=%d/%d\n",
                PWM_D, DER_A, DER_B, PWM_I, IZQ_A, IZQ_B, TRIG_PIN, ECHO_PIN);
  Serial.println("noche e: encoders | r: cero, ruedas quietas | q: matriz estados/transiciones | l: traza si/no");
  Serial.println("noche p: alternar INPUT_PULLUP/INPUT, solo tras confirmar niveles electricos; reinicia captura");
  Serial.println("noche m: iniciar/reintentar MPU | c: calibrar MPU quieto, modo m | u: unico HC-SR04 frontal");
  Serial.println("noche 1/2/3: tu confirmacion FISICA de encoder/MPU/ultra, no aprobacion automatica");
  Serial.println("noche v: armar UN pulso tras confirmar los tres; d/f derecho +/-; i/j izquierdo +/-");
  Serial.println("noche s/espacio/BOOT: parar y desarmar | h: parar y ayuda; USB desconectado cancela motor");
  Serial.println("noche Primer ensayo: potencia de motores apagada, encoders alimentados; ruedas a mano.");
  Serial.println("noche Cambios observados no prueban voltaje, flancos perdidos ni resolucion; sentido +/- es relativo.");
}

void reporteEnc(bool matriz = false) {
  EncoderDiagnostico::Estadistica s[2]; uint32_t perdidos; uint8_t actual[2];
  encoder.leer(s, perdidos, actual);
  for (int i = 0; i < 2; ++i) {
    auto &r = s[i];
    Serial.printf("noche ENC ms=%lu lado=%c AB=%u%u ultimo=%u%u cuenta=%ld +=%lu -=%lu invalidas=%lu sin_cambio=%lu\n",
                  millis(), i == 0 ? 'I' : 'D', actual[i] >> 1, actual[i] & 1,
                  r.ab >> 1, r.ab & 1, r.cuentas, r.positivos, r.negativos, r.invalidas, r.sinCambio);
    Serial.printf("noche CANALES lado=%c A: cambios=%lu rise=%lu fall=%lu irq=%lu | B: cambios=%lu rise=%lu fall=%lu irq=%lu | log_perdidos=%lu\n",
                  i == 0 ? 'I' : 'D', r.cambios[0], r.subidas[0], r.bajadas[0], r.llamadas[0],
                  r.cambios[1], r.subidas[1], r.bajadas[1], r.llamadas[1], perdidos);
    if (matriz) {
      Serial.printf("noche ESTADOS lado=%c entradas_00/01/10/11=%lu/%lu/%lu/%lu\n", i == 0 ? 'I' : 'D',
                    r.estados[0], r.estados[1], r.estados[2], r.estados[3]);
      for (int a = 0; a < 4; ++a)
        Serial.printf("noche MATRIZ desde=%u%u hacia_00/01/10/11=%lu/%lu/%lu/%lu\n", a >> 1, a & 1,
                      r.transiciones[a * 4], r.transiciones[a * 4 + 1], r.transiciones[a * 4 + 2], r.transiciones[a * 4 + 3]);
    }
  }
}

void comenzarMotor(char c) {
  if (moviendo) { parar("orden nueva durante pulso; reenviar tras pausa"); return; }
  if (!armado || !Serial || digitalRead(PIN_PROG) == LOW ||
      (huboMotor && millis() - ultimaParada < PRUEBA_PAUSA_MS)) {
    parar("motor bloqueado: validar sensores, v, soltar BOOT y esperar pausa"); return;
  }
  EncoderDiagnostico::Estadistica s[2]; uint32_t perdidos; uint8_t actual[2];
  encoder.leer(s, perdidos, actual);
  if (s[0].invalidas || s[1].invalidas || perdidos) { parar("captura encoder con errores; volver a diagnosticar"); return; }
  for (int i = 0; i < 2; ++i) { baselineError[i] = s[i].invalidas; baselinePasos[i] = s[i].positivos + s[i].negativos; }
  ladoMotor = (c == 'i' || c == 'j') ? 0 : 1;
  const int pwm = (c == 'f' || c == 'j') ? -PRUEBA_PWM : PRUEBA_PWM;
  modo = Modo::Encoder; armado = false; moviendo = true;
  Serial.printf("noche MOTOR lado=%c orden=%d duracion_ms=%u; verificar rueda fisica y signo encoder\n",
                ladoMotor == 0 ? 'I' : 'D', pwm, PRUEBA_PULSO_MS);
  inicioMotor = millis();
  motores.setMotores(ladoMotor == 1 ? pwm : 0, ladoMotor == 0 ? pwm : 0);
}

void comando(char c) {
  if (c == '\r' || c == '\n') return;
  if (c == 's' || c == ' ' || c == 'h') { parar("comando usuario"); if (c == 'h') ayuda(); return; }
  if (c == 'd' || c == 'f' || c == 'i' || c == 'j') { comenzarMotor(c); return; }
  if (moviendo) { parar("comando durante motor; reenviar con motores detenidos"); return; }
  switch (c) {
    case 'e': armado = false; modo = Modo::Encoder; reporteEnc(); break;
    case 'r':
      armado = confirmaEncoder = false; encoder.reiniciar();
      Serial.println("noche CERO: estados leidos de nuevo; ruedas quietas al reiniciar, medir sin motor."); break;
    case 'l': traza = !traza; Serial.printf("noche traza=%d; contadores siempre activos\n", traza); break;
    case 'p':
      armado = confirmaEncoder = false; pullup = !pullup; encoder.iniciar(pullup);
      Serial.printf("noche entradas=%s; niveles/compatibilidad NO CONFIRMADOS por software\n", pullup ? "INPUT_PULLUP" : "INPUT"); break;
    case 'q': reporteEnc(true); break;
    case 'm':
      armado = confirmaMPU = calibrado = mpuValido = false; modo = Modo::MPU;
      mpuListo = mpu.init();
      Serial.printf("noche MPU init=%s bus=100kHz timeout_ms=%d\n", mpuListo ? "VALIDO" : "FALLO_I2C_IDENTIDAD_O_RANGO", MPU_TIMEOUT_MS); break;
    case 'c':
      if (modo != Modo::MPU || !mpuListo) { Serial.println("noche usar m y resolver inicio MPU antes de c"); break; }
      armado = confirmaMPU = calibrado = false;
      Serial.println("noche CALIBRANDO: quieto y horizontal; motores desarmados, al menos 1 s.");
      calibrado = mpu.calibrar();
      if (!calibrado) mpuListo = mpuValido = false;
      Serial.printf("noche MPU calibracion=%s\n", calibrado ? "COMPLETA_PENDIENTE_PRUEBA_FISICA" : "FALLO_LECTURA_O_MOVIMIENTO"); break;
    case 'u':
      armado = confirmaUltra = false; modo = Modo::Ultra;
      ultra.init(TRIG_PIN, ECHO_PIN, DIST_MAX_CM); ultraIniciado = true;
      nUltra = malasUltra = 0; mediaUltra = m2Ultra = 0;
      ultimaLectura = millis();
      Serial.println("noche ULTRA frontal unico: verificar divisor ECHO antes de medir; resto de sensores sin consultar."); break;
    case '1': {
      EncoderDiagnostico::Estadistica s[2]; uint32_t perdidos; uint8_t actual[2]; encoder.leer(s, perdidos, actual);
      confirmaEncoder = s[0].positivos + s[0].negativos > 0 && s[1].positivos + s[1].negativos > 0 &&
                        !s[0].invalidas && !s[1].invalidas && !perdidos;
      Serial.printf("noche confirmacion USUARIO encoder=%d; requiere repetibilidad, quieto estable y ambos sentidos observados\n", confirmaEncoder); break;
    }
    case '2': confirmaMPU = mpuListo && calibrado && mpuValido;
      Serial.printf("noche confirmacion USUARIO MPU=%d; validar gravedad, respuesta al giro y deriva\n", confirmaMPU); break;
    case '3': confirmaUltra = ultraIniciado && ultra.ultimaLecturaValida() && nUltra >= 10;
      Serial.printf("noche confirmacion USUARIO ultra=%d; comparar regla, estabilidad y medir nivel ECHO\n", confirmaUltra); break;
    case 'v':
      armado = confirmaEncoder && confirmaMPU && confirmaUltra;
      Serial.printf("noche permiso UN pulso=%d (encoder=%d MPU=%d ultra=%d); ruedas levantadas\n", armado, confirmaEncoder, confirmaMPU, confirmaUltra); break;
    default: Serial.println("noche comando desconocido; h muestra ayuda, navegacion inexistente en este firmware"); break;
  }
}

void medirSensores() {
  if (moviendo || millis() - ultimaLectura < 200) return;
  ultimaLectura = millis();
  if (modo == Modo::MPU && mpuListo) {
    float ax, ay, az, gx, gy, gz;
    mpuValido = mpu.leer(ax, ay, az, gx, gy, gz);
    if (!mpuValido) {
      mpuListo = calibrado = confirmaMPU = armado = false;
      Serial.println("noche MPU INVALIDO: fallo I2C; valores descartados, usar m para reintentar");
    } else {
      Serial.printf("noche MPU ms=%lu VALIDO cal=%d ACC_g=%.4f,%.4f,%.4f GYRO_dps=%.3f,%.3f,%.3f\n",
                    millis(), calibrado, ax, ay, az, gx, gy, gz);
    }
  } else if (modo == Modo::Ultra && ultraIniciado) {
    const uint32_t t0 = micros(); ultra.actualizar(); const uint32_t costo = micros() - t0;
    const auto d = ultra.getDiagnostico();
    const bool valido = ultra.ultimaLecturaValida();
    const float cm = valido ? d.pulsoUs / 58.0f : -1.0f;
    if (valido) {
      nUltra++;
      if (nUltra == 1) minimoUltra = maximoUltra = cm;
      minimoUltra = min(minimoUltra, cm); maximoUltra = max(maximoUltra, cm);
      const double delta = cm - mediaUltra; mediaUltra += delta / nUltra; m2Ultra += delta * (cm - mediaUltra);
    } else { malasUltra++; confirmaUltra = armado = false; }
    Serial.printf("noche ULTRA ms=%lu %s raw_cm=%.2f filtrado_cm=%d pulso_us=%lu ECHO=%d/%d lectura_us=%lu timeout_us=%lu\n",
                  millis(), d.estado, cm, valido ? ultra.getDistancia() : -1, d.pulsoUs,
                  d.echoAntes, d.echoDespues, costo, DIST_MAX_CM * 58UL + 1000UL);
    Serial.printf("noche ESTABILIDAD validas=%lu invalidas=%lu media_cm=%.2f sd_cm=%.2f min/max=%.2f/%.2f (objeto fijo)\n",
                  nUltra, malasUltra, mediaUltra, nUltra > 1 ? sqrt(m2Ultra / (nUltra - 1)) : 0.0,
                  nUltra ? minimoUltra : 0.0f, nUltra ? maximoUltra : 0.0f);
  }
}
} // namespace

void setup() {
  // Precargar LOW antes de habilitar salidas; no controla los niveles durante reset/sin alimentacion.
  for (int pin : {PWM_D, PWM_I, DER_A, DER_B, IZQ_A, IZQ_B}) gpio_set_level(static_cast<gpio_num_t>(pin), 0);
  pinMode(PWM_D, OUTPUT); pinMode(PWM_I, OUTPUT);
  motores.init(); motores.detener();
  pinMode(PIN_PROG, INPUT_PULLUP);
  capacidadSerial = Serial.setTxBufferSize(8192);
  Serial.begin(115200); Serial.setTxTimeoutMs(0);
  encoder.iniciar(pullup);
  ultimoLoop = millis();
  // No Wire.begin, TRIG ni PWM de movimiento al arrancar; no espera conexion USB.
}

void loop() {
  const uint32_t ahora = millis();
  if (moviendo) {
    if (!Serial || digitalRead(PIN_PROG) == LOW || ahora - ultimoLoop > 150) parar("USB/BOOT/control atrasado");
    else if (ahora - inicioMotor >= PRUEBA_PULSO_MS) { parar("fin de pulso"); reporteEnc(); }
    else {
      EncoderDiagnostico::Estadistica s[2]; uint32_t perdidos; uint8_t actual[2]; encoder.leer(s, perdidos, actual);
      if (s[0].invalidas != baselineError[0] || s[1].invalidas != baselineError[1] || perdidos) {
        confirmaEncoder = false; parar("encoder invalido o registro saturado durante motor");
      } else if (ahora - inicioMotor > 1200 && s[ladoMotor].positivos + s[ladoMotor].negativos == baselinePasos[ladoMotor]) {
        confirmaEncoder = false; parar("sin pasos encoder en motor comandado");
      }
    }
  }
  ultimoLoop = ahora;
  if (!Serial) { armado = false; usbAnterior = false; return; }
  if (!usbAnterior) {
    usbAnterior = true;
    Serial.printf("noche USB conectado; reset_reason=%d; compilado=%s %s\n", esp_reset_reason(), __DATE__, __TIME__);
    ayuda();
  }
  if (Serial.available()) comando(Serial.read());
  medirSensores();
  // Consumir registros fuera de ISR; el conteo no depende de poder imprimir cada evento.
  for (int n = 0; n < 8 && Serial.availableForWrite() >= 128; ++n) {
    EncoderDiagnostico::Evento e;
    if (!encoder.siguiente(e)) break;
    if (traza) Serial.printf("noche EDGE us=%lu lado=%c AB=%u%u>%u%u paso=%d irq=%c%c %s\n",
                            e.us, e.rueda == 0 ? 'I' : 'D', e.antes >> 1, e.antes & 1,
                            e.ahora >> 1, e.ahora & 1, e.paso,
                            e.origen / 2 == 0 ? 'I' : 'D', e.origen % 2 == 0 ? 'A' : 'B',
                            (e.antes ^ e.ahora) == 3 ? "INVALIDA" : "VALIDA");
  }
  if (millis() - ultimoReporte >= 1000) {
    ultimoReporte = millis();
    if (modo == Modo::Encoder || moviendo) reporteEnc();
  }
}
