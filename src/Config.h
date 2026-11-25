#ifndef CONFIG_H
#define CONFIG_H

// Placa confirmada: Waveshare ESP32-S3-ETH, logica de 3.3 V.
// Prueba encoders + MPU: avance de 20 cm y giro derecho; CAMARA DESCONECTADA.
// GPIO43/44 son UART0, reutilizados como GPIO; el monitor usa USB nativo 19/20.
// IO21 reservado al RGB integrado. IN4 izquierdo conectado a IO15, no IO21.
// Motores por comandos de banco o a tras calibrar. Cuchilla desconectada.
// Ultrasonico fuera de esta prueba: no se inicializa ni se leen sus pines.

// ---------- Driver de motores ----------
// 1 = L298N (actual)   2 = IBT-2 / BTS7960 (futuro)
#define DRIVER_MOTORES 1

// ---------- Comportamiento ----------
#define UMBRAL_OBS_CM   25    // distancia minima a un obstaculo (cm)
#define VELOCIDAD_BASE  180   // PWM 0-255

#if DRIVER_MOTORES == 1
  // L298N: ENA/ENB = velocidad (PWM), IN1..IN4 = sentido
  #define PWM_D 47    // ENA
  #define DER_A 48    // IN1
  #define DER_B 15    // IN2
  #define PWM_I 40   // ENB
  #define IZQ_A 42    // IN3
  #define IZQ_B 41    // IN4
#else
  // IBT-2: cada motor usa dos PWM (R = adelante, L = atras).
  // R_EN y L_EN de cada driver van puenteados a 3.3 V.
  #define D_RPWM 5
  #define D_LPWM 6
  #define I_RPWM 10
  #define I_LPWM 9
#endif

// ---------- Ultrasonico HC-SR04 ----------
// ATENCION: ECHO sale a 5 V. Usar divisor 1k / 2k antes de entrar al ESP32.
#define TRIG_PIN     1
#define ECHO_PIN     2    // HREF de camara; usar divisor de tension en ECHO
#define DIST_MAX_CM  200

// ---------- Encoders de cuadratura (senales a 3.3 V) ----------
#define ENC_IZQ_A 39
#define ENC_IZQ_B 38
#define ENC_DER_A 44
#define ENC_DER_B 43

// ---------- MPU6050 (I2C) ----------
// MPU se inicializa al seleccionar su prueba. No compartir I2C16/17 con HC-05.
#define I2C_SDA 16
#define I2C_SCL 17
#define MPU_MUESTRAS_CALIBRACION 500
#define MPU_DIRECCION 0x68     // AD0 a GND; cambiar a 0x69 si AD0 esta a 3.3V
#define MPU_TIMEOUT_MS 25

// ---------- HC-05 en Serial1 ----------
// RX del ESP32 <- TX del HC-05 ; TX del ESP32 -> RX del HC-05
#define BT_RX (-1)             // HC-05 deshabilitado: no dejar el define vacio
#define BT_TX (-1)             // GPIO16 reservado a SDA del MPU
#define BT_BAUDIOS 9600

// ---------- Boton y LED ----------
#define PIN_PROG 0              // boton BOOT de la placa
#define LED_PROG (-1)          // LED externo deshabilitado; GPIO20 pertenece al USB
#define RGB_LED_PIN 21         // RGB integrado de Waveshare; IN4 no puede usarlo

// ---------- Rutina de banco en main.cpp ----------
#define PRUEBA_PWM 120         // PWM 0..255; puede no alcanzar para arrancar todo motor
#define PRUEBA_PULSO_MS 3000   // Pulso de banco por motor, sin exigir MPU ni calibracion
#define PRUEBA_PAUSA_MS 500    // Parada entre movimientos e inversiones

// ---------- Recorrido: 20 cm y giro derecho de 90 grados ----------
#define DIAMETRO_RUEDA_CM 6.0f
// Cuentas x4 POR VUELTA DE RUEDA, no por vuelta del eje del motor.
// Cero = falta medir: comandos r, una vuelta de cada rueda hacia adelante, k.
#define CUENTAS_VUELTA_IZQ 0.0f
#define CUENTAS_VUELTA_DER 0.0f
#define SIGNO_ENCODER_IZQ 1
#define SIGNO_ENCODER_DER 1
#define SIGNO_GIRO_DERECHA (-1) // Z del MPU hacia arriba: derecha produce gz negativo
#define RECORRIDO_CM 20.0f
#define GIRO_DERECHA_GRADOS 90.0f
#define CONTROL_INTERVALO_MS 20
#define AVANCE_TIMEOUT_MS 10000
#define GIRO_TIMEOUT_MS 8000
#define SIN_PULSOS_TIMEOUT_MS 1500

#endif
