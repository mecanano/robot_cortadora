#include <Arduino.h>
#include "esp32-hal-rgb-led.h"
#include <math.h>
#include "Config.h"
#include "Robot.h"

Robot robot;
enum class Etapa { Espera, Encoders, MPU, Motor, MotorPausa, Avance, Pausa, Giro, Error };
Etapa etapa = Etapa::Espera;
float cuentasVueltaI = CUENTAS_VUELTA_IZQ, cuentasVueltaD = CUENTAS_VUELTA_DER;
int signoI = SIGNO_ENCODER_IZQ, signoD = SIGNO_ENCODER_DER;
bool capturandoVuelta = false;
unsigned long inicioEtapa = 0, ultimoControl = 0, ultimoReporte = 0;
unsigned long ultimoPulsoI = 0, ultimoPulsoD = 0, ultimoProgresoGiro = 0;
unsigned long ultimaMuestraUs = 0;
unsigned long ultimaParadaMotor = 0;
bool huboMovimiento = false;
bool probarIzquierdoDespues = false;
long cuentasI = 0, cuentasD = 0, anteriorI = 0, anteriorD = 0;
unsigned long erroresI = 0, erroresD = 0;
float cmI = 0, cmD = 0, yaw = 0, referenciaGiro = 0;
float ax = 0, ay = 0, az = 0, gx = 0, gy = 0, gz = 0;
constexpr float PI_RUEDA = 3.14159265358979323846f;
constexpr float TOLERANCIA_GIRO = 2.0f;

// El ultrasonico queda sin iniciar y sus pines no se configuran.
constexpr int pines[] = {
  ENC_IZQ_A, ENC_IZQ_B, ENC_DER_A, ENC_DER_B, I2C_SDA, I2C_SCL, RGB_LED_PIN,
#if DRIVER_MOTORES == 1
  PWM_D, DER_A, DER_B, PWM_I, IZQ_A, IZQ_B
#else
  D_RPWM, D_LPWM, I_RPWM, I_LPWM
#endif
};
constexpr bool mapaValido() {
  for (size_t i = 0; i < sizeof(pines) / sizeof(pines[0]); ++i) {
    int p = pines[i];
    if (p < 0 || p == 19 || p == 20 || (p >= 33 && p <= 37)) return false;
    for (size_t j = 0; j < i; ++j) if (p == pines[j]) return false;
  }
  return true;
}
static_assert(mapaValido(), "Conflicto GPIO entre encoders, MPU, RGB y motores");
static_assert(DIAMETRO_RUEDA_CM > 0 && RECORRIDO_CM > 0, "Distancias deben ser positivas");
static_assert(SIGNO_GIRO_DERECHA == 1 || SIGNO_GIRO_DERECHA == -1, "Signo MPU debe ser +1 o -1");
static_assert((SIGNO_ENCODER_IZQ == 1 || SIGNO_ENCODER_IZQ == -1) &&
              (SIGNO_ENCODER_DER == 1 || SIGNO_ENCODER_DER == -1), "Signos de encoder deben ser +1 o -1");
static_assert(PRUEBA_PWM > 0 && PRUEBA_PWM <= 255, "PWM fuera de rango");

void color(uint8_t r, uint8_t g, uint8_t b) { rgbLedWrite(RGB_LED_PIN, r, g, b); }
bool enMovimiento() { return etapa == Etapa::Motor || etapa == Etapa::MotorPausa || etapa == Etapa::Avance || etapa == Etapa::Giro || etapa == Etapa::Pausa; }
void leerEncoders() { robot.sensor.leerEncoders(cuentasI, cuentasD, erroresI, erroresD); }

void detener() {
  probarIzquierdoDespues = false;
  if (enMovimiento()) { ultimaParadaMotor = millis(); huboMovimiento = true; }
  robot.motor.detener();
  etapa = Etapa::Espera;
  capturandoVuelta = false;
  color(0, 20, 0);
}
void fallar(const char *motivo) {
  probarIzquierdoDespues = false;
  if (enMovimiento()) { ultimaParadaMotor = millis(); huboMovimiento = true; }
  robot.motor.detener();
  etapa = Etapa::Error;
  capturandoVuelta = false;
  color(24, 0, 0);
  Serial.printf("PARADA: %s. Corregir y volver a iniciar por comando.\n", motivo);
}
void menu() {
  Serial.println("\nENCODERS + MPU: ultrasonico DESACTIVADO, camara desconectada.");
  Serial.println("IN4 izquierdo=IO15; RGB=IO21. Ruedas de 6 cm. Prototipo sin cuchilla.");
  Serial.println("e: leer encoders | p: detectar/leer MPU | c: calibrar MPU quieto y horizontal");
  Serial.println("BANCO (ruedas levantadas): d/f derecho adelante/atras; i/j izquierdo adelante/atras; b ambos adelante");
  Serial.println("t: secuencia UNA vez: derecho 3000 ms, pausa 500 ms, izquierdo 3000 ms y parada");
  Serial.printf("Cada comando de banco mueve %u ms a PWM %d y para; no necesita MPU ni calibracion.\n", PRUEBA_PULSO_MS, PRUEBA_PWM);
  Serial.println("r: comenzar calibracion encoders (cero); girar CADA rueda UNA vuelta hacia ADELANTE");
  Serial.println("k: guardar cuentas de esas vueltas en RAM (repetir al reiniciar si Config sigue en cero)");
  Serial.println("g: ver giro manual con MPU calibrado (derecha debe aumentar grados_derecha)");
  Serial.println("a: avanzar 20 cm, parar, girar 90 grados a la derecha y detenerse UNA vez");
  Serial.println("s o espacio: parar | h: parar y mostrar ayuda | BOOT pulsado: parar");
  Serial.println("RGB: espera verde, encoders cian, MPU amarillo, banco derecho azul/izquierdo magenta/ambos blanco, error rojo.");
  Serial.println("Primero verificar a mano sentidos/cuentas y MPU. Prueba de recorrido en zona despejada.");
  Serial.printf("Encoder I=%d/%d D=%d/%d | MPU SDA/SCL=%d/%d | cuentas/vuelta=%.0f/%.0f\n",
                ENC_IZQ_A, ENC_IZQ_B, ENC_DER_A, ENC_DER_B, I2C_SDA, I2C_SCL,
                cuentasVueltaI, cuentasVueltaD);
}

bool prepararMPU() {
  if (!robot.sensor.mpuDisponible() && !robot.sensor.iniciarMPU()) {
    fallar("MPU no detectado o I2C fallo; revisar SDA16/SCL17 y alimentacion");
    return false;
  }
  return true;
}

void guardarVuelta() {
  leerEncoders();
  if (!capturandoVuelta || erroresI || erroresD || labs(cuentasI) < 4 || labs(cuentasD) < 4) {
    fallar("Calibracion encoder incompleta: usar r y una vuelta por rueda, sin errores de transicion");
    return;
  }
  cuentasVueltaI = static_cast<float>(labs(cuentasI));
  cuentasVueltaD = static_cast<float>(labs(cuentasD));
  signoI = cuentasI > 0 ? 1 : -1;
  signoD = cuentasD > 0 ? 1 : -1;
  detener();
  Serial.printf("Calibracion RAM: cuentas/vuelta I=%.0f D=%.0f; signos I=%d D=%d\n",
                cuentasVueltaI, cuentasVueltaD, signoI, signoD);
  Serial.printf("Resolucion lineal I=%.3f cm/cuenta D=%.3f cm/cuenta. Comparar con regla.\n",
                PI_RUEDA * DIAMETRO_RUEDA_CM / cuentasVueltaI,
                PI_RUEDA * DIAMETRO_RUEDA_CM / cuentasVueltaD);
  Serial.println("Para conservar: copiar cuentas y signos a CUENTAS_VUELTA_IZQ/DER y SIGNO_ENCODER_IZQ/DER en Config.h.");
}

void iniciarRecorrido() {
  if (enMovimiento()) { detener(); Serial.println("DETENIDO. Esperar la pausa antes de iniciar otro movimiento."); return; }
  detener();
  if (huboMovimiento && millis() - ultimaParadaMotor < PRUEBA_PAUSA_MS) { Serial.println("Esperar pausa entre movimientos."); return; }
  if (cuentasVueltaI <= 0 || cuentasVueltaD <= 0) { fallar("Faltan cuentas por vuelta: r, una vuelta por rueda, k"); return; }
  if (!robot.sensor.mpuDisponible() || !robot.sensor.mpuCalibrado()) { fallar("MPU sin calibrar: usar c en reposo"); return; }
  if (!robot.sensor.leerMPU(ax, ay, az, gx, gy, gz)) { fallar("Lectura MPU invalida"); return; }
  if (fabsf(gz) > 3.0f) { fallar("Robot girando o calibracion MPU inestable"); return; }
  if (digitalRead(PIN_PROG) == LOW) { fallar("Soltar BOOT antes de iniciar"); return; }
  robot.sensor.reiniciarEncoders();
  leerEncoders();
  anteriorI = cuentasI; anteriorD = cuentasD;
  cmI = cmD = yaw = referenciaGiro = 0;
  inicioEtapa = ultimoControl = ultimoPulsoI = ultimoPulsoD = millis();
  ultimaMuestraUs = micros();
  etapa = Etapa::Avance;
  color(0, 0, 24);
  Serial.println("INICIO: avance por encoders, luego giro derecho por giroscopio. s/BOOT detiene.");
  robot.motor.setMotores(PRUEBA_PWM, PRUEBA_PWM);
}

void iniciarPruebaMotor(char comando) {
  if (enMovimiento()) { detener(); Serial.println("DETENIDO. Esperar la pausa y reenviar el comando."); return; }
  detener();
  if (huboMovimiento && millis() - ultimaParadaMotor < PRUEBA_PAUSA_MS) { Serial.println("Esperar pausa entre movimientos."); return; }
  if (digitalRead(PIN_PROG) == LOW) { fallar("Soltar BOOT antes de iniciar"); return; }
  int pwmD = 0, pwmI = 0;
  const char *nombre = "Ambos adelante";
  switch (comando) {
    case 'd': pwmD = PRUEBA_PWM; nombre = "Derecho adelante"; break;
    case 'f': pwmD = -PRUEBA_PWM; nombre = "Derecho atras"; break;
    case 'i': pwmI = PRUEBA_PWM; nombre = "Izquierdo adelante"; break;
    case 'j': pwmI = -PRUEBA_PWM; nombre = "Izquierdo atras"; break;
    case 'b': pwmD = pwmI = PRUEBA_PWM; break;
    default: return;
  }
  robot.sensor.reiniciarEncoders();
  inicioEtapa = millis(); etapa = Etapa::Motor;
  color(pwmI != 0 ? 20 : 0, comando == 'b' ? 20 : 0, 20);
  Serial.printf("BANCO: %s | PWM D/I=%d/%d | pulso=%u ms. s/BOOT detiene.\n", nombre, pwmD, pwmI, PRUEBA_PULSO_MS);
#if DRIVER_MOTORES == 1
  Serial.printf("PINES L298N: DERECHO ENA=%d IN1=%d IN2=%d | IZQUIERDO ENB=%d IN3=%d IN4=%d\n",
                PWM_D, DER_A, DER_B, PWM_I, IZQ_A, IZQ_B);
#endif
  robot.motor.setMotores(pwmD, pwmI);
}

void procesarComando(char c) {
  if (c == '\r' || c == '\n') return;
  if (c == 't') {
    iniciarPruebaMotor('d');
    if (etapa == Etapa::Motor) probarIzquierdoDespues = true;
    return;
  }
  if (c == 'd' || c == 'f' || c == 'i' || c == 'j' || c == 'b') { iniciarPruebaMotor(c); return; }
  if (c == 'a') { iniciarRecorrido(); return; }
  if (c != 's' && c != ' ' && c != 'h' && c != 'e' && c != 'p' && c != 'c' &&
      c != 'r' && c != 'k' && c != 'a' && c != 'g') return;
  // k debe conservar la marca de calibracion iniciada con r.
  if (c == 'k') { robot.motor.detener(); guardarVuelta(); return; }
  detener();
  switch (c) {
    case 'h': menu(); break;
    case 'e': etapa = Etapa::Encoders; color(0, 20, 20); break;
    case 'r':
      robot.sensor.reiniciarEncoders();
      capturandoVuelta = true; etapa = Etapa::Encoders; color(0, 20, 20);
      Serial.println("CERO. Girar cada rueda UNA vuelta completa hacia adelante, luego enviar k.");
      break;
    case 'p': case 'g': case 'c':
      color(20, 20, 0);
      if (!prepararMPU()) break;
      if (c == 'c') {
        Serial.println("CALIBRANDO MPU: mantener robot quieto y horizontal. Motores detenidos.");
        if (!robot.sensor.calibrarMPU()) { fallar("Calibracion MPU fallo: movimiento o I2C"); break; }
        Serial.println("MPU calibrado. g permite revisar el signo girando a mano hacia la derecha.");
      }
      etapa = Etapa::MPU; yaw = 0; ultimaMuestraUs = micros(); ultimoControl = millis();
      break;
    default: Serial.println("DETENIDO."); break;
  }
}

void actualizarControl() {
  if (etapa == Etapa::MotorPausa) {
    if (millis() - inicioEtapa >= PRUEBA_PAUSA_MS) {
      robot.sensor.reiniciarEncoders();
      etapa = Etapa::Motor;
      color(20, 0, 20);
      Serial.printf("BANCO: Izquierdo adelante | PWM D/I=0/%d | pulso=%u ms. s/BOOT detiene.\n", PRUEBA_PWM, PRUEBA_PULSO_MS);
      inicioEtapa = millis();
      robot.motor.setMotores(0, PRUEBA_PWM);
    }
    return;
  }
  if (etapa == Etapa::Motor) {
    if (millis() - inicioEtapa >= PRUEBA_PULSO_MS) {
      robot.motor.detener();
      leerEncoders();
      Serial.printf("FIN BANCO: I=%ld err=%lu | D=%ld err=%lu. No determina cuentas por vuelta.\n", cuentasI, erroresI, cuentasD, erroresD);
      if (probarIzquierdoDespues) {
        probarIzquierdoDespues = false;
        etapa = Etapa::MotorPausa; inicioEtapa = millis(); color(0, 20, 0);
        Serial.println("PAUSA: ambos detenidos; sigue izquierdo.");
      } else detener();
    }
    return; // Prueba de motores independiente del MPU y del recorrido.
  }
  if (etapa != Etapa::MPU && !enMovimiento()) return;
  unsigned long ahora = millis();
  if (ahora - ultimoControl < CONTROL_INTERVALO_MS) return;
  if (enMovimiento() && ahora - ultimoControl > 150) { fallar("Control atrasado mas de 150 ms"); return; }
  ultimoControl = ahora;
  if (!robot.sensor.leerMPU(ax, ay, az, gx, gy, gz) || !isfinite(gz)) {
    fallar("Error I2C/MPU: no usar valores anteriores como validos"); return;
  }
  unsigned long muestraUs = micros();
  float dt = (muestraUs - ultimaMuestraUs) / 1000000.0f;
  ultimaMuestraUs = muestraUs;
  if (enMovimiento() && dt > 0.15f) { fallar("Muestra MPU demasiado tardia"); return; }
  yaw += gz * dt; // Giro relativo integrado; requiere Z vertical y calibracion.
  if (!enMovimiento()) return;
  leerEncoders();
  if (cuentasI != anteriorI) { ultimoPulsoI = ahora; anteriorI = cuentasI; }
  if (cuentasD != anteriorD) { ultimoPulsoD = ahora; anteriorD = cuentasD; }
  if (erroresI || erroresD) { fallar("Transicion encoder invalida durante recorrido"); return; }

  if (etapa == Etapa::Avance) {
    cmI = cuentasI * signoI * (PI_RUEDA * DIAMETRO_RUEDA_CM / cuentasVueltaI);
    cmD = cuentasD * signoD * (PI_RUEDA * DIAMETRO_RUEDA_CM / cuentasVueltaD);
    if (ahora - inicioEtapa > AVANCE_TIMEOUT_MS) { fallar("Timeout avance"); return; }
    if (cuentasI * signoI < -2 || cuentasD * signoD < -2) { fallar("Rueda gira al reves de la calibracion"); return; }
    if (fabsf(yaw) > 20.0f || fabsf(cmI - cmD) > 5.0f) { fallar("Desvio excesivo en avance"); return; }
    bool faltaI = cmI < RECORRIDO_CM, faltaD = cmD < RECORRIDO_CM;
    if (!faltaI && !faltaD) {
      robot.motor.detener(); etapa = Etapa::Pausa; inicioEtapa = ahora; color(0, 20, 0);
      Serial.println("AVANCE completado segun encoders; pausa antes del giro."); return;
    }
    if ((faltaI && ahora - ultimoPulsoI > SIN_PULSOS_TIMEOUT_MS) ||
        (faltaD && ahora - ultimoPulsoD > SIN_PULSOS_TIMEOUT_MS)) { fallar("Sin progreso en una rueda"); return; }
    int correccion = constrain(static_cast<int>((cmI - cmD) * 8.0f), -25, 25);
    int pwmD = faltaD ? constrain(PRUEBA_PWM + correccion, 0, 255) : 0;
    int pwmI = faltaI ? constrain(PRUEBA_PWM - correccion, 0, 255) : 0;
    robot.motor.setMotores(pwmD, pwmI);
  } else if (etapa == Etapa::Pausa) {
    if (ahora - inicioEtapa < PRUEBA_PAUSA_MS) return;
    etapa = Etapa::Giro; inicioEtapa = ultimoPulsoI = ultimoPulsoD = ultimoProgresoGiro = ahora;
    yaw = referenciaGiro = 0; color(20, 0, 20);
    Serial.println("GIRO: derecho atras, izquierdo adelante. Objetivo: 90 grados derecha.");
    robot.motor.setMotores(-PRUEBA_PWM, PRUEBA_PWM);
  } else if (etapa == Etapa::Giro) {
    float derecha = yaw * SIGNO_GIRO_DERECHA;
    if (derecha < -8.0f) { fallar("Giro con signo contrario: revisar motores y orientacion/signo Z del MPU"); return; }
    if (derecha >= GIRO_DERECHA_GRADOS - TOLERANCIA_GIRO) {
      robot.motor.detener();
      Serial.printf("FIN: encoder I/D=%.2f/%.2f cm; giro estimado=%.1f grados derecha. Verificar con regla/escuadra.\n", cmI, cmD, derecha);
      detener(); return;
    }
    if (derecha - referenciaGiro >= 1.0f) { referenciaGiro = derecha; ultimoProgresoGiro = ahora; }
    if (ahora - inicioEtapa > GIRO_TIMEOUT_MS || ahora - ultimoProgresoGiro > SIN_PULSOS_TIMEOUT_MS ||
        ahora - ultimoPulsoI > SIN_PULSOS_TIMEOUT_MS || ahora - ultimoPulsoD > SIN_PULSOS_TIMEOUT_MS) {
      fallar("Giro sin progreso o timeout"); return;
    }
    int pwm = derecha > 65.0f ? max(70, PRUEBA_PWM * 3 / 4) : PRUEBA_PWM;
    robot.motor.setMotores(-pwm, pwm);
  }
}

void reportar() {
  if (millis() - ultimoReporte < 250) return;
  ultimoReporte = millis();
  leerEncoders();
  if (etapa == Etapa::Encoders)
    Serial.printf("ENC I=%ld err=%lu | D=%ld err=%lu | cuentas/vuelta=%.0f/%.0f\n", cuentasI, erroresI, cuentasD, erroresD, cuentasVueltaI, cuentasVueltaD);
  else if (etapa == Etapa::Motor || etapa == Etapa::MotorPausa)
    Serial.printf("BANCO ENC I=%ld err=%lu | D=%ld err=%lu\n", cuentasI, erroresI, cuentasD, erroresD);
  else if (etapa == Etapa::MPU)
    Serial.printf("MPU ACC[g]=%.3f,%.3f,%.3f GYRO[dps]=%.2f,%.2f,%.2f | grados_derecha=%.2f | calibrado=%d\n", ax, ay, az, gx, gy, gz, yaw * SIGNO_GIRO_DERECHA, robot.sensor.mpuCalibrado());
  else if (enMovimiento())
    Serial.printf("ETAPA=%s | cm I/D=%.2f/%.2f | giro_derecha=%.1f | cuentas I/D=%ld/%ld\n",
                  etapa == Etapa::Avance ? "AVANCE" : etapa == Etapa::Pausa ? "PAUSA" : "GIRO", cmI, cmD, yaw * SIGNO_GIRO_DERECHA, cuentasI, cuentasD);
}

void setup() {
  robot.motor.init();
  color(0, 20, 0);
  pinMode(PIN_PROG, INPUT_PULLUP);
  Serial.begin(115200); Serial.setTxTimeoutMs(0);
  robot.sensor.init(false, false); // Ni MPU ni ultrasonico: ningun pulso en IO1/IO2.
  robot.sensor.iniciarEncoders();
  menu();
}

void loop() {
  if (digitalRead(PIN_PROG) == LOW && enMovimiento()) { fallar("BOOT pulsado"); return; }
  if (Serial.available()) procesarComando(Serial.read());
  actualizarControl();
  reportar();
}
