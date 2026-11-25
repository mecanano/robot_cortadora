> noche boceto conservado como referencia hist?rica; contiene estados y propuestas anteriores que contradicen el firmware actual.
> noche la revisi?n cr?tica y el plan vigente est?n en [PLAN_HASTA_16_NOVIEMBRE.md](PLAN_HASTA_16_NOVIEMBRE.md), el estado en [AVANCES.md](AVANCES.md) y las reglas en [RULES.md](RULES.md).
> noche el usuario exige movimiento aut?nomo para el 16 de noviembre de 2026; los ejemplos de c?digo y comandos de este boceto no se ejecutaron durante la revisi?n.

# Robot cortacésped con ESP32-S3: plan de desarrollo detallado

*Documento de trabajo · versión del 6 de noviembre de 2026 · etapa de pruebas, sin cuchilla*

## 1. Cómo leer este documento

Cada afirmación lleva una marca, siguiendo la metodología del proyecto:

- ✅ **Confirmado:** comprobado con evidencia (código leído, documentación oficial o una medición tuya).
- ⚠️ **Supuesto o pendiente:** propuesto, deducido o a la espera de una prueba.
- ❌ **Incorrecto o bloqueado:** contradice el código, el hardware o un requisito.

Regla general: **compilar no es probar.** Una función se da por buena solo cuando se la vio funcionar en el hardware.

## 2. Objetivo y alcance

**Objetivo inmediato:** recolectar datos reales de ultrasonido, MPU6050 y encoders, y comprobar que el código funciona. Es el cierre de la etapa de investigación y la etapa que sigue es la recolección de datos.

**Contexto:** es una etapa de pruebas. No hay cuchilla y el robot no es el producto final.

**Modo de datos: streaming puro.** El ESP32 mide y manda por BLE. No guarda nada en flash ni en SD. Los datos viven solo en la laptop (o el celular) y el ESP32 los olvida. Consecuencias:

1. Sin nadie conectado, las muestras se pierden. Hay que conectarse **antes** de mover el robot.
2. Si se corta la conexión, se pierde ese tramo. Para detectarlo, cada muestra lleva un **número de secuencia** además de `millis`.
3. Quien guarda el archivo es el receptor, no el ESP32.

**Fuera de alcance por ahora:** cuchilla, navegación autónoma real, seguridad formal, migración a IBT-2, comandos BLE de movimiento y cámara (queda para una fase posterior).

## 3. Estado real del proyecto hoy

| Tema | Estado | Detalle |
| --- | --- | --- |
| Código compila | ✅ | Lo informaste vos. La auditoría de lectura no compiló. |
| Firmware actual flasheado | ⚠️ | Dijiste que todavía no lo flasheaste. Se confirma en la Parte 0. |
| Git | ❌ | El repositorio existe pero **no tiene commits**. Todo figura sin seguimiento. La rama actual es `prueba-encoders`. |
| Placa | ✅ | **Waveshare ESP32-S3-ETH** (se ve el chip Ethernet W5500 en tu foto). |
| Placa en PlatformIO | ⚠️ | Está configurada como `esp32-s3-devkitc-1` con perfil de 8 MB de flash. La documentación de Waveshare indica 16 MB de flash y 8 MB de PSRAM. |
| Entorno | ✅ | pioarduino 55.03.312 y Arduino-ESP32 3.3.12 (leídos en disco). PlatformIO Core 6.2.0 viene de la auditoría previa. |
| MPU6050 | ⚠️ | Funciona con otro código (tu prueba). Falta probarlo en este firmware, donde hoy está omitido (`init(false)`). |
| Ultrasónico | ❌ | Sin lecturas. El módulo Robobloq 1022056 probablemente **no es un HC-SR04** (ver Parte 3). |
| Encoders | ⚠️ | El conteo x4 ya existe en `Sensores.cpp`, sin probar con hardware. Pulsos por vuelta desconocidos. |
| Motores | ⚠️ | JGB37-520 supuesto, con L298N. Tensión y reducción sin confirmar. |
| BLE | ❌ | No implementado. `Bluetooth.cpp` usa `Serial1` para un HC-05. |
| Mapas de pines | ❌ | Hay tres versiones distintas y ninguna es compatible con el conector de tu placa. |
| `test_hw/encoders` | ❌ | Carpeta vacía. El entorno `test_encoders` compila todo `src/`. |
| Telemetría actual | ⚠️ | CSV por USB. El recolector Python del material de IA espera JSON y lo descartaría. |

### Hallazgos de la auditoría de lectura

- ✅ `Config.h` asigna los motores a los GPIO 5 a 10, que **no existen en tu conector**.
- ✅ GPIO 16 y 17 están asignados a dos funciones cada uno (encoder y HC-05 o MPU).
- ✅ `main.cpp` tiene seleccionada una prueba conjunta que **inicializa los motores**, aunque solo se quieran probar sensores.
- ✅ El mensaje de la prueba de ultrasónico dice TRIG 12 y ECHO 11, pero la configuración real es 43 y 2.
- ✅ El comentario de ECHO en `Config.h` dice «SD MISO», que no corresponde.
- ✅ `LED_BUILTIN` apunta al GPIO 48 en el perfil usado, pero en esta placa el LED RGB está en el GPIO 21.
- ✅ `leerMPU` informa éxito sin comprobar una desconexión posterior, y el modo robot puede enviar `NaN` si falta el sensor.
- ✅ `MAPA_MOVIMIENTO_VALIDADO` está definido pero no condiciona nada.
- ✅ Hay en la carpeta archivos ZIP, temporales de Office (`~$...`) y un archivo vacío con el nombre del proyecto que no deberían ir a git.
- ✅ La carpeta de MicroPython/Pico W es otro firmware, para otra plataforma. No forma parte del ESP32.

## 4. Hardware

### 4.1 La placa

Waveshare ESP32-S3-ETH. La documentación oficial indica 16 MB de flash y 8 MB de PSRAM. Tiene Ethernet W5500, ranura microSD y conector de cámara en la propia placa.

### 4.2 Pines del conector

Waveshare expone 25 GPIO: 0, 1, 2, 3, 15, 16, 17, 18, 21 y del 33 al 48. Los GPIO **33 a 37 están ocupados internamente** y no se pueden usar. Quedan **20 pines útiles**:

| GPIO | Qué más tiene conectado | Para tu robot |
| --- | --- | --- |
| 0 | Botón BOOT, ⚠️ pin de arranque | Evitar |
| 1, 2 | Cámara (VSYNC, HREF) | Libres si no hay cámara |
| 3 | Cámara (XCLK), ⚠️ pin de arranque | Evitar |
| 15, 18 | Cámara (D6, D7) | Libres si no hay cámara |
| 16, 17 | Nada | **Los más limpios** |
| 21 | LED RGB | Usable, pero el LED recibe la señal |
| 38, 39, 40, 41, 42 | Cámara (D5, PCLK, D4, D0, D3) | Libres si no hay cámara |
| 43, 44 | ⚠️ UART0 (TX y RX) | Evitar para señales críticas |
| 45, 46 | Cámara (D1, D2), ⚠️ pines de arranque | Evitar |
| 47, 48 | Cámara (SCL, SDA) | Libres si no hay cámara |

### 4.3 Lo que no se puede usar

- ❌ **GPIO 4 a 7:** los usa la microSD, internamente, y no salen al conector.
- ❌ **GPIO 9 a 14:** los usa el Ethernet W5500, internamente. Aunque no uses Ethernet, **no se liberan**.
- ❌ **GPIO 8:** no figura entre los expuestos.
- ❌ **GPIO 33 a 37:** ocupados internamente.
- ❌ **Pines junto al RJ45** (rotulados 1, 2, 3, 4, + y −): son el puerto PoE, no son GPIO. Pueden tener tensiones altas si se conecta un módulo PoE. No tocarlos.
- ⚠️ **GPIO 19 y 20:** USB nativo, que se usa para el monitor serie con `ARDUINO_USB_CDC_ON_BOOT=1`.

Por eso los pines que se habían pensado al principio (4, 5, 8, 9 y 10 a 13) **no se pueden cablear** en esta placa.

### 4.4 Mapa de pines propuesto (sin cámara)

Todos los pines están numerados según GPIO. Es una propuesta ⚠️ que depende de dos decisiones: no conectar cámara en esta fase y resolver el ultrasónico (Parte 3).

| Función | GPIO | Observación |
| --- | --- | --- |
| MPU6050 SDA / SCL | 16 / 17 | Los más limpios. Alimentado a 3,3 V |
| Ultrasónico 1: TRIG / ECHO | 1 / 2 | ECHO con divisor, si resulta ser un HC-SR04 |
| Ultrasónico 2: TRIG / ECHO | 15 / 18 | Igual |
| Encoder izquierdo A / B | 38 / 39 |  |
| Encoder derecho A / B | 43 / 44 | ⚠️ UART0: revisar conteos falsos al encender |
| Motores: ENA (PWM), IN1, IN2 | 40, 41, 42 | Reservados, no se usan todavía |
| Motores: ENB (PWM), IN3, IN4 | 47, 48, 21 | El 21 solo para dirección, por el LED |

Total: 16 pines, que son exactamente los útiles sin cámara y sin los pines de arranque. **No queda margen.**

Si el ultrasónico resulta ser un módulo con bus de dos hilos, ocuparía solo 2 pines (o ninguno, si comparte el bus con el MPU) y el mapa se relaja.

### 4.5 Alimentación

| Componente | Tensión | Fuente |
| --- | --- | --- |
| MPU6050 | 3,3 V | Pin 3V3 de la placa |
| Encoders | 3,3 V (⚠️ si su rango lo permite) | Pin 3V3 |
| Ultrasónicos | 5 V | Pin VBUS (5 V del USB) |
| Motores JGB37-520 | ⚠️ Según la etiqueta; suelen ser 12 V | **Batería aparte**, con GND común |

- El L298N entrega entre 1,5 y 2 V menos de lo que recibe y soporta 2 A por canal. Los arranques del motor pueden resetear el ESP32 si comparten fuente con el USB.
- Todo comparte **GND común**.
- Los dos niveles de tensión (3,3 V y 5 V) conviven en el robot, siempre con protecciones en las señales.

### 4.6 Protecciones obligatorias

1. **Divisor de tensión en cada ECHO de 5 V:** 1 kΩ entre el ECHO y el GPIO, y 2 kΩ entre el GPIO y GND. Quedan cerca de 3,3 V. El ESP32-S3 no tolera 5 V en sus GPIO.
2. **Convertidor de nivel bidireccional (BSS138, 4 canales)** para cualquier bus de 5 V (por ejemplo, el ultrasónico si resulta ser I2C). El divisor de resistencias no sirve para señales bidireccionales.
3. **Resistencia de 1 kΩ en serie** en cada cable desconocido durante las pruebas de identificación.
4. No conectar nada a los pines del puerto PoE.
5. Conectar siempre GND antes que las señales, y no alimentar un módulo con la polaridad invertida.

## 5. Plan por partes

Orden: **0 → 1 → 2** (ya hay datos reales por BLE) → **3** → **4** → **5** → **6** → **7**. Las partes 8, 9 y 10 quedan para después.

Hay dos carriles que corren en paralelo:

- **Software:** Partes 0, 1 y 2. Funcionan sin ultrasónico.
- **Hardware:** identificar el ultrasónico (Parte 3).

### Parte 0: base del proyecto

**Objetivo:** tener un punto de partida seguro, un solo mapa de pines y pruebas aisladas.

**Pasos:**

1. **Limpiar la carpeta.** Sacar los ZIP y los temporales de Office (`~$...`) de la carpeta del proyecto, o ignorarlos. Agregar al `.gitignore`:

```
~$*
*.zip
.pio/
compile_commands.json
```

2. **Commit de línea base.** Como el repositorio no tiene commits, la rama `prueba-encoders` es provisoria:

```
git branch -m main
git add .gitignore platformio.ini README.md src
git commit -m "Linea base: estado actual que compila"
git checkout -b pruebas
```

Conviene revisar `git status` antes de confirmar que no entre nada de más (por ejemplo, la carpeta de MicroPython). 3. **Un solo mapa de pines en `Config.h`.** Reemplazar las asignaciones por el mapa de la sección 4.4. Cambios mínimos y sin tocar la lógica:

- Motores a 40, 41, 42, 47, 48 y 21.
- MPU a SDA 16 y SCL 17.
- Ultrasónico y encoders según el mapa.
- Corregir el comentario de ECHO y el mensaje TRIG 12 / ECHO 11.
- Que `LED_PROG` no use el GPIO 48.
- Actualizar el `README.md`, que hoy contradice el código.

4. **Aislar las pruebas.** Una carpeta por prueba y un entorno propio en `platformio.ini`, para no tocar `src/`:

```
test_hw/
  vivo/main.cpp
  mpu/main.cpp
  ultrasonico/main.cpp
  encoders/main.cpp
```

```ini
[env:test_vivo]
extends = env:esp32s3
build_src_filter = -<*> +<../test_hw/vivo/main.cpp>
```

Cada entorno nuevo repite el patrón con su carpeta. Verificar que el filtro compila solo ese archivo. 5. **Prueba de que el ESP32 está vivo** (`test_hw/vivo/main.cpp`):

```cpp
#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("ESP32-S3 vivo");
}

void loop() {
  Serial.println(millis());
  delay(500);
}
```

Compilar con `pio run -e test_vivo`, flashear con `pio run -e test_vivo -t upload` y abrir `pio device monitor`.

**Método que se repite en cada paso:** commit, cambiar una sola cosa, compilar, flashear, mirar el resultado y hacer otro commit si anda (o volver con `git checkout .` si no).

**Criterio de éxito:**

- ✅ El repositorio tiene el commit de línea base.
- ✅ `Config.h` tiene un único mapa, con todos los pines dentro de los 20 útiles.
- ✅ El monitor muestra el mensaje y `millis` subiendo.

**Si falla:**

| Síntoma | Qué revisar |
| --- | --- |
| No aparece el puerto | Cable USB (muchos son solo de carga) u otro puerto de la placa |
| El monitor no muestra nada | `monitor_speed = 115200` y los `build_flags` de USB CDC. Cerrar otros programas que ocupen el puerto |
| No sube el firmware | Mantener BOOT al conectar, o cerrar el monitor |

### Parte 1: MPU6050 por USB

**Objetivo:** confirmar que el acelerómetro y el giroscopio dan valores razonables en este firmware.

**Conexión (⚠️ a verificar con el cableado real):**

| MPU6050 | ESP32-S3-ETH |
| --- | --- |
| VCC | 3V3 |
| GND | GND |
| SDA | GPIO 16 |
| SCL | GPIO 17 |
| AD0 | GND (dirección 0x68) |

**Prueba mínima** (`test_hw/mpu/main.cpp`), con `Wire` directo, sin biblioteca:

```cpp
#include <Arduino.h>
#include <Wire.h>

const uint8_t MPU = 0x68;

void setup() {
  Serial.begin(115200);
  Wire.begin(16, 17);
  Wire.beginTransmission(MPU);
  Wire.write(0x6B);
  Wire.write(0);
  Serial.println(Wire.endTransmission() == 0 ? "MPU OK" : "MPU NO RESPONDE");
}

void loop() {
  Wire.beginTransmission(MPU);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU, (uint8_t)14);
  int16_t ax = Wire.read() << 8 | Wire.read();
  int16_t ay = Wire.read() << 8 | Wire.read();
  int16_t az = Wire.read() << 8 | Wire.read();
  Wire.read(); Wire.read();
  int16_t gx = Wire.read() << 8 | Wire.read();
  int16_t gy = Wire.read() << 8 | Wire.read();
  int16_t gz = Wire.read() << 8 | Wire.read();
  Serial.printf("%.2f %.2f %.2f | %.1f %.1f %.1f\n",
    ax / 16384.0, ay / 16384.0, az / 16384.0,
    gx / 131.0, gy / 131.0, gz / 131.0);
  delay(200);
}
```

Las constantes 16384 y 131 corresponden a los rangos por defecto (±2 g y ±250 °/s).

**Criterio de éxito:**

- ✅ Quieto y plano, un eje marca cerca de 1 g (normalmente Z) y los otros dos cerca de 0.
- ✅ Los tres ejes del giroscopio quedan cerca de 0 °/s.
- ✅ Al inclinarlo, el valor de 1 g pasa de un eje al otro.

**Si falla:**

| Síntoma | Qué revisar |
| --- | --- |
| «MPU NO RESPONDE» | Alimentación de 3,3 V, GND común, SDA y SCL no invertidos, soldaduras |
| Valores en cero o fijos | El módulo sigue dormido: confirmar la escritura al registro 0x6B |
| Valores muy ruidosos | Cables largos o flojos, y motores cerca |

Si nada responde, correr un **escáner I2C**: debe aparecer `0x68` (o `0x69` si AD0 está en alto).

**Después, dentro del firmware real:** pasar `SDA_MPU` y `SCL_MPU` en `Config.h` a 16 y 17, y activar el MPU en `Sensores::init` (hoy `main.cpp` lo omite). La calibración promedia 500 lecturas con 2 ms de espera, o sea al menos 1 segundo, con el robot **completamente quieto**.

### Parte 2: telemetría BLE con el MPU

**Objetivo:** que el ESP32 mande las mediciones por BLE a la laptop, sin alterar la navegación ni los motores. Es la Etapa 2 del documento maestro, con el MPU como primer sensor.

**Diseño de comunicación:**

- BLE nativo del ESP32-S3, sin HC-05. La biblioteca BLE viene en el framework instalado (✅ confirmado en la auditoría); los ejemplos de la versión 3.3.12 son la referencia para la API.
- **Servicio GATT propio**, con UUID generados por vos (no reutilizar los estándar), y una característica de telemetría con propiedad `NOTIFY`.
- Nombre de publicidad fijo y reconocible (por ejemplo `RobotCesped`).
- **Reanudar la publicidad al desconectarse**, para poder volver a conectar sin reiniciar la placa.
- **Sin comandos BLE de movimiento** en esta etapa.
- **USB Serial se conserva** para diagnóstico. No se elimina.
- El envío se hace solo si hay un cliente conectado y suscrito, y se programa con `millis`, sin `delay`.

**Formato del mensaje (versión 1):** una línea de texto CSV terminada en salto de línea.

```
v1,seq,ms,dist_cm,ax,ay,az,gx,gy,gz
```

| Campo | Unidad | Nota |
| --- | --- | --- |
| `v1` |  | Versión del formato. Si el formato cambia, cambia este número |
| `seq` | cuenta | Empieza en 1 y sube de a uno. Los saltos indican muestras perdidas |
| `ms` | milisegundos | `millis()` desde el arranque |
| `dist_cm` | centímetros | `-1` significa sin lectura (así lo devuelve hoy `medirDistancia()`) |
| `ax, ay, az` | g | Aceleración |
| `gx, gy, gz` | grados por segundo | Velocidad angular |

La línea se arma solo con datos que existen y están verificados. **No se incluyen** batería, velocidad real de ruedas, posición ni encoders mientras no se midan. Mientras falte el ultrasónico, `dist_cm` va en `-1`.

**Tamaño y MTU.** Por defecto una notificación BLE lleva solo 20 bytes útiles (MTU de 23 menos 3 de cabecera). Una línea como la de arriba mide entre 45 y 100 bytes. Dos soluciones, que pueden combinarse:

1. **Negociar un MTU mayor** (hasta unos 247 bytes). Suele funcionar con laptops y celulares modernos (⚠️ a comprobar con tu equipo) y hay que leer el MTU negociado en la conexión.
2. **Fragmentar:** si la línea no entra en `MTU − 3` bytes, enviarla en trozos. El receptor reensambla hasta encontrar el salto de línea.

Otra alternativa es un formato binario compacto de tamaño fijo. Para empezar conviene el CSV de texto, porque se depura a simple vista.

**Frecuencia objetivo:** unas 2 muestras por segundo. ⚠️ No se debe afirmar que son exactamente 2 Hz: los bloqueos del código pueden hacerla irregular, y la frecuencia real se mide con `ms` y `seq`.

**Archivos a tocar:** `src/Bluetooth.h`, `src/Bluetooth.cpp`, `src/Config.h` (UUID, nombre y período) y `README.md`. No se tocan motores, sensores ni navegación, salvo que una dependencia real lo exija y se autorice aparte.

**Antes de dejar `Serial1`:** buscar **todos** sus usos. Hoy la clase `Bluetooth` envía por `Serial1` (HC-05) y duplica por USB la línea `DIST: ... | ACC: ... | GYRO: ...` desde el modo robot. Solo después de revisar eso se deja de usar la UART para telemetría.

**Pasos de implementación:**

1. Inicializar el servidor BLE.
2. Crear el servicio y la característica.
3. Armar y enviar la línea de telemetría.
4. Gestionar conexión y desconexión (reanudar publicidad).
5. Resolver MTU y tamaño.
6. Mantener el USB Serial.
7. Compilar y revisar el diff.

**Criterio de finalización de la implementación:** compilación satisfactoria y revisión de código. La conexión física queda pendiente hasta probarlo en la placa.

**Receptor en la laptop (Windows con Bluetooth 5.0).** Hay una decisión abierta, porque dijiste que el firmware está en C/C++ y no queremos sumar un lenguaje innecesario:

| Opción | Lenguaje | Ventaja | Desventaja |
| --- | --- | --- | --- |
| nRF Connect (escritorio o celular) | Ninguno | Confirma que llegan los datos | Guardar un CSV es incómodo |
| Web Bluetooth en Chrome | HTML y JavaScript | No se instala nada | Hay que escribir una página corta |
| Script con la biblioteca `bleak` | Python | Lo más corto para guardar CSV | Requiere Python |
| Aplicación .NET | C# | Nativa de Windows | Más trabajo inicial |
| USB Serial y un programa que guarde el log | Ninguno | Sirve para validar sensores ya | No es BLE |

**Recomendación de orden:** validar sensores por USB Serial guardando el texto, luego comprobar BLE con nRF Connect y recién después elegir cómo guardar el CSV.

**Prueba física (Etapa 3):**

1. Flashear solo con tu autorización.
2. Buscar el dispositivo desde la aplicación exploradora.
3. Conectar y habilitar las notificaciones.
4. Verificar formato, unidades e integridad.
5. Desconectar y reconectar, y confirmar que la publicidad se recupera.
6. Registrar muestras en pruebas controladas.
7. Comparar con lo que sale por USB.
8. Medir la frecuencia efectiva y buscar saltos en `seq`.

**Riesgos:** alcance de la conexión, MTU menor al esperado, pérdida de notificaciones y bloqueos del código que vuelven irregular el muestreo.

### Parte 3: ultrasónico del kit Robobloq

**Objetivo:** obtener distancias confiables, o decidir a tiempo cambiar de sensor.

#### 3.1 Qué se sabe

| Dato | Estado | Fuente |
| --- | --- | --- |
| Alimentación de 5 V, ángulo de hasta 20°, rango de 5 a 250 cm | ✅ | Tienda oficial de Robobloq |
| Conector RJ11 y biblioteca propia para el IDE de Arduino | ✅ | Tienda oficial |
| Se conecta al puerto RJ11 negro de las placas Qmind | ✅ | Manual |
| La placa original usa un chip 328P (Qmind), un Mega 2560 (Qmind Plus) o ESP32 (QmindX) | ✅ | Tiendas y repositorios |
| Existe un esquema oficial en PDF del módulo | ✅ | Repositorio de la comunidad (no pude leer su contenido) |
| Otra tienda lo describe como I²C, de 3,3 a 5 V y 3 a 400 cm | ⚠️ | No coincide con la oficial. Poco confiable |
| Una persona reportó que su versión con LEDs RGB se manejaba con I2C por software y no logró leer distancias | ⚠️ | Un solo caso, de otra variante |

#### 3.2 Qué no se sabe

- La función de cada uno de los 6 pines del RJ11.
- Si el tuyo es la versión con LEDs o el módulo ultrasónico solo.
- El protocolo de comunicación y sus comandos.
- Qué son exactamente el «puerto 100 y 101» (o 102) que mencionaste. ⚠️ Hipótesis: identificadores del software de Robobloq. Si el módulo es direccionable, dos sensores podrían compartir los mismos dos cables.

#### 3.3 Lo que ya medimos

- El cable tiene **6 hilos**. VCC y GND ya están identificados.
- Los hilos sin continuidad con nada de la placa son probablemente **NC** (sin conexión). Quedan **aislados con cinta** y sin conectar.
- Los hilos que dan una resistencia muy alta con continuidad hacia componentes de la placa son **señales reales**. El valor se anotó como «10»: ⚠️ hay que confirmar la unidad (lo más probable es 10 MΩ, no 10 Ω ni 10 mΩ).
- Uno de esos hilos llega al **receptor** del ultrasónico.
- Pendiente: a qué va cada uno de los otros, cuántos NC hay y si algún hilo llega a un chip.

#### 3.4 Seguridad (sin excepciones)

1. Alimentar el módulo con **5 V**, con GND común al ESP32.
2. **No conectar ningún hilo de señal a un GPIO** hasta saber si es entrada o salida del módulo.
3. Si algún hilo mide cerca de 5 V en reposo, tiene pull-up a 5 V: **usar convertidor de nivel**, no divisor.
4. **No unir esas líneas al bus I2C del MPU** (3,3 V) sin convertidor.
5. Un hilo que va directo al receptor puede ser una señal cruda de milivoltios a 40 kHz: **no es legible por un GPIO**.

#### 3.5 Procedimiento de identificación

1. **Esquema oficial.** Descargar `Ultrasonic_Sensor-V1.0-SCH.pdf` del repositorio `aretche/recursos-robobloq` y compartirlo. Es el atajo más rápido: dice la función de cada pin del RJ11.
2. **Mirar la placa:** si hay un microcontrolador u otro chip grande, anotar lo impreso en él. Eso indica el protocolo.
3. **Tester, con el módulo apagado:** por cada hilo, resistencia contra VCC y contra GND en los dos sentidos, y destino de la continuidad (chip, resistencia, transductor u otro hilo).
4. **Tester, con el módulo a 5 V:** tensión de cada hilo contra GND. Cerca de 5 V indica pull-up.
5. **Escuchar con el ESP32 sin manejar ninguna línea** (divisor de 1 kΩ y 2 kΩ en cada hilo, hacia GPIO 38 a 41):

```cpp
#include <Arduino.h>

const int PINES[4] = {38, 39, 40, 41};
const char NOMBRES[4] = {'A', 'B', 'C', 'D'};

void setup() {
  Serial.begin(115200);
  delay(1500);
  for (int i = 0; i < 4; i++) pinMode(PINES[i], INPUT);
}

void loop() {
  int ultimo[4], cambios[4] = {0, 0, 0, 0};
  for (int i = 0; i < 4; i++) ultimo[i] = digitalRead(PINES[i]);
  unsigned long t0 = millis();
  while (millis() - t0 < 2000) {
    for (int i = 0; i < 4; i++) {
      int v = digitalRead(PINES[i]);
      if (v != ultimo[i]) { cambios[i]++; ultimo[i] = v; }
    }
  }
  for (int i = 0; i < 4; i++)
    Serial.printf("%c: nivel=%d cambios=%d | ", NOMBRES[i], ultimo[i], cambios[i]);
  Serial.println();
}
```

| Resultado | Significado |
| --- | --- |
| Nivel 1 fijo y sin cambios | Pull-up en reposo, compatible con un bus |
| Nivel 0 fijo y sin cambios | En bajo en reposo, o NC |
| Cambios constantes | El módulo transmite por sí solo |

6. **Escaneo I2C** solo si hay pull-ups y **con convertidor de nivel** (BSS138): probar las dos orientaciones de SDA y SCL. Si aparece una dirección, el módulo es I2C. Aun así, **leer la distancia requiere comandos que Robobloq no publicó**.

#### 3.6 Decisión con límite de tiempo

Fijar un límite (por ejemplo, una o dos sesiones de trabajo). Si con el esquema y el chip no queda claro el protocolo, **se cambia a un HC-SR04 genérico**, que cuesta poco, está documentado y funciona con el código de abajo. Los módulos del kit quedan para pruebas aparte. Esto evita perder semanas con un módulo propietario y atrasar el objetivo real, que son los datos.

#### 3.7 Código de prueba para un HC-SR04

Sirve solo si el sensor es un HC-SR04 o compatible. TRIG en GPIO 1 y ECHO en GPIO 2, con divisor en el ECHO, alimentado a 5 V desde VBUS.

```cpp
#include <Arduino.h>

const int TRIG = 1;
const int ECHO = 2;

void setup() {
  Serial.begin(115200);
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
  digitalWrite(TRIG, LOW);
  delay(1000);
}

void loop() {
  digitalWrite(TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  unsigned long dur = pulseIn(ECHO, HIGH, 30000);
  if (dur == 0) Serial.println("Sin lectura");
  else Serial.println(dur * 0.0343 / 2.0, 1);
  delay(100);
}
```

**Criterio de éxito:** con un objeto a 10, 30 y 100 cm medidos con regla, el error es de 1 a 2 cm. El intervalo mínimo entre mediciones es de 60 ms, que es lo que ya usa el firmware (rango aceptado de 2 a 200 cm, mediana de tres lecturas, timeout de `pulseIn` de unos 12,6 ms).

| Síntoma | Qué revisar |
| --- | --- |
| Siempre «Sin lectura» | 5 V, GND común, TRIG y ECHO no invertidos, divisor |
| Valores que saltan | Cables flojos, superficie que refleja mal (tela, ángulo) |
| Siempre el mismo valor | Medir con el tester el ECHO mientras dispara |

**Dos sensores:** medirlos **por turnos**, nunca a la vez, para que no se interfieran. Para ahorrar un pin se pueden compartir los ECHO con dos diodos antes del divisor (⚠️ comprobar con el tester), pero solo conviene si falta ese pin.

### Parte 4: encoders

**Objetivo:** contar pulsos de cada rueda y medir cuántas cuentas da una vuelta.

**Supuestos ⚠️:** los motores se parecen a un **JGB37-520** con encoder Hall integrado y reductora. Ese tipo de motor suele tener 6 cables: dos de motor y cuatro de encoder (alimentación, GND, canal A y canal B). Los encoders se alimentan a 3,3 V.

**Datos que hay que medir o confirmar:**

| Dato | Cómo se obtiene |
| --- | --- |
| Pulsos por vuelta de rueda | Girar la rueda una vuelta a mano y contar |
| Relación de reducción | Etiqueta del motor (algo como 1:30), o deducirla del conteo |
| Encoder en el eje del motor o en la rueda | Mirar el montaje |
| Tipo de salida | Si no cuenta, probar `INPUT_PULLUP` (colector abierto) |
| Diámetro de rueda y distancia entre ruedas | Medir |
| Velocidad máxima esperada | Calcular con los datos anteriores |

Fórmula de referencia: `cuentas por vuelta de rueda = pulsos por canal × 4 (cuadratura) × reducción`. Por ejemplo, 11 × 4 × 30 = 1320. **Es solo un ejemplo:** el número real se mide.

**Qué ya existe en el código (✅):** `Sensores.cpp` implementa conteo x4 con signo mediante interrupciones en ambos flancos de A y B, cuenta transiciones inválidas como errores, protege las lecturas con sección crítica y acepta `r` por serie para reiniciar. Nada de eso se probó con hardware.

**Prueba aislada** (`test_hw/encoders/main.cpp`), con las ruedas **a mano** y los motores sin conectar al L298N. Versión mínima para validar el cableado (cuenta un flanco de A, x1):

```cpp
#include <Arduino.h>

const int A_IZQ = 38, B_IZQ = 39;
const int A_DER = 43, B_DER = 44;
volatile long izq = 0, der = 0;

void IRAM_ATTR isrIzq() { izq += digitalRead(B_IZQ) ? -1 : 1; }
void IRAM_ATTR isrDer() { der += digitalRead(B_DER) ? -1 : 1; }

void setup() {
  Serial.begin(115200);
  pinMode(A_IZQ, INPUT); pinMode(B_IZQ, INPUT);
  pinMode(A_DER, INPUT); pinMode(B_DER, INPUT);
  attachInterrupt(A_IZQ, isrIzq, RISING);
  attachInterrupt(A_DER, isrDer, RISING);
}

void loop() {
  Serial.printf("izq=%ld der=%ld\n", izq, der);
  delay(200);
}
```

Luego se pasa a la decodificación x4 que ya trae el proyecto. El periférico PCNT del ESP32-S3 se evalúa **después**, si hace falta, y la estrategia definitiva se ajusta al hardware real.

**Protocolo físico:**

1. Poner los contadores en cero.
2. Una vuelta completa de la rueda izquierda en un sentido; anotar las cuentas. Repetir en sentido contrario.
3. Lo mismo con la rueda derecha.
4. Repetir **5 veces** cada una para ver la dispersión.
5. Girar rápido y lento, para ver si se pierden cuentas.
6. Dejar la rueda **quieta 60 segundos**: las cuentas no deben cambiar y las transiciones inválidas deben ser 0.
7. Reiniciar los estados con las ruedas quietas, como pide el comentario del código antes de instalar las interrupciones.

**Criterio de éxito:**

- ✅ Girar en un sentido suma cuentas y en el otro resta (si sale al revés, se invierte el signo o se intercambian A y B).
- ✅ Las cinco repeticiones dan cuentas por vuelta muy parecidas.
- ✅ Quieto, no cambia nada.
- ✅ Las transiciones inválidas se mantienen en 0 o muy cerca.

| Síntoma | Qué revisar |
| --- | --- |
| Las cuentas no se mueven | 3,3 V, GND, cableado, `INPUT_PULLUP` |
| Cuentas falsas al encender | Los GPIO 43 y 44 son UART0 (⚠️); mover esos encoders a otro pin |
| Errores de transición | Cables largos o flojos, o giro demasiado rápido |

**Regla:** por BLE se mandan las **cuentas crudas** (un entero por rueda). La velocidad y la distancia se calculan después en la laptop, y **no se considera disponible la velocidad real** hasta que su cálculo se implemente y se verifique. Los contadores `long` no tienen protección contra desbordamiento: para pruebas cortas no es un problema.

### Parte 5: todos los sensores juntos

**Objetivo:** una sola línea de datos con MPU, ultrasónico y encoders, sin conflictos de pines.

**Formato versión 2** (el número de versión cambia porque cambia el formato):

```
v2,seq,ms,dist1_cm,dist2_cm,ax,ay,az,gx,gy,gz,enc_izq,enc_der
```

Si hay un solo ultrasónico, se omite `dist2_cm` y el formato se documenta de nuevo. Un sensor que no está o no responde se informa con el valor de sin lectura (`-1` en distancias), **nunca con un valor inventado**.

**Pasos, de a uno (commit entre cada uno):**

1. Ultrasónico + MPU. Verificar.
2. Sumar los encoders. Verificar.
3. Revisar que ningún pin esté repetido en `Config.h`.
4. Medir cuánto dura una vuelta del ciclo principal.
5. Comprobar que la línea llega completa por USB.

**Criterio de éxito:** datos coherentes de los tres sensores en la misma línea, sin reinicios, y con `seq` sin saltos en una prueba de un minuto.

### Parte 6: motores con L298N

**Precondición:** Partes 1 a 5 aprobadas. Los motores son la parte que puede dañar algo, así que van después de tener todo lo demás medido.

**Qué dice el código (✅):** driver L298N seleccionado (`DRIVER_MOTORES = 1`); dos señales de dirección y una de PWM por motor; velocidad base 180 sobre 255; `setMotores` limita a −255 a 255 y el signo define la dirección; `analogWrite` con valores por defecto del núcleo (1000 Hz y 8 bits). En el arranque se configuran las salidas y se llama a `detener()` (PWM cero).

**Conexión (con el mapa nuevo):**

| Motor | PWM | Dirección |
| --- | --- | --- |
| Derecho | ENA en GPIO 40 | IN1 en 41, IN2 en 42 |
| Izquierdo | ENB en GPIO 47 | IN3 en 48, IN4 en 21 |

**Alimentación:** batería propia para los motores, con la tensión que diga su etiqueta (⚠️ los JGB37-520 suelen ser de 12 V), y **GND común** con el ESP32. No alimentar los motores desde el USB.

**Pasos:**

1. Con los motores **desconectados** del L298N, verificar las señales de dirección y PWM con el tester o un LED.
2. Conectar la batería al L298N. Robot **levantado en un soporte**, ruedas al aire.
3. Arrancar con PWM bajo. Usar la prueba existente: 900 ms avanzando y 1000 ms detenido.
4. Comprobar el sentido de giro; si sale al revés, invertir los cables del motor o las señales IN.
5. Observar si el ESP32 se **reinicia** al arrancar los motores.
6. Con el motor girando, leer los encoders y comparar con el sentido esperado.
7. Recién después, probar con el robot en el piso.

**Qué revisar al arranque y reinicio:** que ningún motor se mueva solo, que los pines de dirección queden en estado conocido y que `detener()` se llame antes de cualquier otra cosa. ⚠️ Un PWM en cero no equivale a frenado: depende de cómo quede el puente H.

| Síntoma | Qué revisar |
| --- | --- |
| Se reinicia el ESP32 | Batería aparte, GND común, un capacitor cerca del driver |
| El motor no gira | Puentes en ENA y ENB (algunos módulos los traen), PWM, tensión |
| Gira al revés | Invertir cables o señales IN |
| Se calienta el L298N | Corriente de arranque alta; recordar el límite de 2 A por canal |

**Limitaciones:** el L298N pierde cerca de 2 V; si el motor es de 12 V recibirá unos 10 V. Alcanza para pruebas. **Sin cuchilla ni motores de corte** durante esta fase. Un interruptor físico en la batería es una forma simple de cortar la potencia si algo se descontrola.

### Parte 7: recolección de datos reales

**Objetivo:** obtener series de datos guardadas que se puedan analizar.

**Preguntas que los datos tienen que responder** (definirlas antes de grabar):

1. ¿Cuánto varía el ultrasónico con un objeto fijo a distancias conocidas?
2. ¿Cuánta deriva tiene el giroscopio con el robot quieto?
3. ¿Las cuentas del encoder coinciden con una vuelta real?
4. ¿Cuánta vibración meten los motores en el MPU?
5. ¿Cuál es la frecuencia efectiva de la telemetría y cuántas muestras se pierden?

**Sesiones sugeridas:**

| Sesión | Condición | Duración orientativa | Responde |
| --- | --- | --- | --- |
| S1 | Robot quieto sobre una mesa | 5 minutos | 2 y 5 |
| S2 | Objeto fijo a 10, 30 y 100 cm | 100 muestras por distancia | 1 |
| S3 | Ruedas giradas a mano | 5 vueltas por rueda y sentido | 3 |
| S4 | Motores en soporte | Varios minutos | 3 y 4 |
| S5 | Robot en el piso | Varias pasadas | 4 y 5 |

**Qué registrar de cada sesión:** fecha, descripción, superficie, alimentación usada, commit del firmware y versión del formato de datos. Nombre de archivo sugerido: `AAAA-MM-DD_sesion_descripcion.csv`.

**Antes de cada sesión:**

- Conectar el receptor **antes** de mover el robot.
- Una prueba de un minuto, comprobando que `seq` no tiene saltos.
- Hacer commit del firmware que se va a usar.

**Análisis posterior:**

| Métrica | Cómo se calcula |
| --- | --- |
| Frecuencia efectiva | Muestras recibidas dividido el tiempo transcurrido |
| Pérdidas | Saltos en `seq` |
| Irregularidad | Diferencias entre `ms` consecutivos |
| Ruido del ultrasónico | Desvío estándar con el objeto fijo |
| Deriva del giroscopio | Pendiente de `gx`, `gy`, `gz` con el robot quieto |
| Vibración | Dispersión de la aceleración con motores en marcha |

**Limitación conocida:** el código tiene esperas bloqueantes, así que el muestreo es irregular. Hay dos caminos: aceptar ese sesgo en los primeros datos (y registrarlo), o hacer antes una versión mínima no bloqueante solo de la lectura de sensores.

**Criterios de aceptación ⚠️ (propuestas, para que las decidas):** por ejemplo, al menos el 95 % de las muestras sin salto de `seq`, y error del ultrasónico de 2 cm o menos contra regla. Lo importante es fijar números antes de medir.

### Parte 8: microSD (opcional)

- ✅ La ranura microSD usa los GPIO 4 a 7, internos, así que **no cuesta ningún pin** del conector.
- ❌ No hay integración de SD en el firmware C++ actual.
- ⚠️ Si se usa como respaldo local, contradice el modo de streaming puro: es una **decisión explícita** que hay que tomar.
- Se prueba aparte, siguiendo el ejemplo del fabricante, con la tarjeta formateada como corresponda (⚠️ verificar). Escribir en bloques y vaciar el búfer cada cierto tiempo, sin bloquear el ciclo principal.

### Parte 9: cámara y reparto con un Arduino Nano

Se deja **para después** de la recolección. Por ahora se usan los pines de la cámara como GPIO comunes, lo que solo es válido sin cámara conectada.

**Por qué la cámara usa tantos pines:** es una cámara de interfaz paralela. Manda 8 bits a la vez para mover imágenes grandes.

| Grupo | Pines |
| --- | --- |
| Datos D0 a D7 | 8 |
| PCLK, XCLK, VSYNC, HREF | 4 |
| SDA y SCL de configuración | 2 |
| **Total** | **14** |

Con la cámara conectada quedan libres solo los GPIO 16, 17, 21, 43 y 44 (el 0 es el botón BOOT). El robot completo necesita 16, así que **no entra todo en esta placa**. Desactivar Ethernet no libera pines.

**Opciones:**

| Opción | Descripción | Dificultad |
| --- | --- | --- |
| **A. ESP32 + Arduino Nano por UART** | El ESP32 hace cámara, SD, BLE y MPU. El Nano hace motores, encoders y ultrasónicos | Media |
| B. Cámara en otra placa | Placa de cámara aparte, y esta placa para el robot | Media |
| C. Cámara SPI | Menos pines, pero deja cero margen, obliga a usar pines de arranque, es lenta y obliga a rehacer el entrenamiento | Alta |
| D. Todo en esta placa | No entra | No viable |

**Recomendación: A, por UART y no por I2C.** El Nano trabaja a 5 V y podría meter 5 V en el bus I2C del ESP32 y del MPU. Por UART solo hace falta un divisor en el TX del Nano. Además, los bloqueos del ultrasónico ocurren en el Nano y no frenan el BLE ni la cámara, y el ECHO a 5 V entra directo.

| Placa | Función y pines (⚠️ propuesta) |
| --- | --- |
| ESP32 | MPU en 16/17, UART al Nano en 43/44, cámara con sus 14 pines |
| Nano | Motores ENA y ENB (PWM) en D5 y D6, IN1 a IN4 en D4, D7, D8 y D12; encoder izquierdo en D2/D11 y derecho en D3/D10; ultrasónicos en A0 a A3; UART en D0/D1 |

D0 y D1 son también el USB del Nano: hay que desconectar esos cables para cargarle programas.

**Para la cámara hace falta:** configurar la PSRAM de 8 MB y la flash de 16 MB en `platformio.ini` (hoy no están), y decidir si se usa para decisiones en tiempo real o para tomar fotos y entrenar después.

### Parte 10: mejoras posteriores

Se definen con los datos de la Parte 7.

**Código bloqueante (✅ confirmado en la auditoría):**

| Dónde | Duración |
| --- | --- |
| Arranque de cada prueba | 500 ms |
| TRIG | 2 µs y 10 µs |
| `pulseIn` | Hasta 12,6 ms de timeout |
| Calibración del MPU | 500 esperas de 2 ms (1 s o más) |
| Evasión | 300 + 700 + 600 + 200 = 1800 ms |
| Final del ciclo robot | 200 ms; con evasión suma 2000 ms en esa vuelta |
| Prueba de motores | 900 ms y 1000 ms |

**Línea de trabajo:**

1. **Control no bloqueante:** máquina de estados con transiciones temporizadas, período de control verificable y latencia medida antes y después de cada cambio. No se crean tareas FreeRTOS ni se asignan núcleos por anticipado.
2. **Fallos de sensores:** definir qué pasa ante cada uno (hoy `leerMPU` no detecta una desconexión y puede mandar `NaN`).
3. **Modos y seguridad formal:** remoto, autónomo, pérdida de comunicación, parada de emergencia. Se definen **después** de decidir los modos.
4. **Migración a IBT-2 (BTS7960):** etapa separada, sin mezclarla con BLE. Verificar el modelo, la alimentación, los pines de habilitación y los estados de arranque. Cada motor usa 2 pines de PWM y no necesita pines de dirección: 4 en total en vez de 6.
5. **Navegación y autonomía:** calibración, estimación de movimiento, control de velocidad. No se presupone aprendizaje automático ni cámara hasta que haya una necesidad y datos suficientes.
6. **Validación integral:** arranque, fallos de sensores, conexión BLE, integridad de datos, lectura de encoders, funcionamiento prolongado y pruebas físicas progresivas, con criterios medibles.

## 6. Metodología y reglas de trabajo

**Siete pasos por etapa:**

1. **Verificar:** inspeccionar código, configuración, dependencias y estado.
2. **Analizar:** causas, alternativas y dependencias.
3. **Explicar:** solución, archivos afectados, riesgos y pruebas.
4. **Decidir:** autorizar los cambios importantes.
5. **Ejecutar:** solo lo aprobado.
6. **Verificar el resultado:** compilar, revisar el diff, correr las pruebas autorizadas.
7. **Continuar:** solo cuando el resultado esté revisado.

**Reglas:**

- No modificar muchas partes a la vez.
- No asumir que el código, el cableado o el hardware funcionan sin verificarlos.
- No cambiar de framework ni actualizar dependencias sin motivo concreto.
- No tocar motores ni navegación en una etapa de comunicación.
- No declarar una prueba física como hecha si solo se compiló.
- Revisar el diff después de cada etapa.
- Mantener separados lo confirmado, lo supuesto y lo pendiente.

**Qué no se hace todavía:** comandos BLE de movimiento, migración de drivers junto con BLE, reescribir la navegación, tareas FreeRTOS sin medir, afirmar autonomía, eliminar el USB Serial, probar con cuchillas.

**Informe al terminar cada etapa:** objetivo y alcance, estado anterior y hallazgos, archivos modificados y motivo, cambios, compilación y resultado, pruebas realmente hechas, pruebas pendientes, riesgos y limitaciones, y decisión recomendada para la etapa siguiente.

**Cómo pedirle cosas a la IA del entorno:** un objetivo por pedido; contexto con lo confirmado y lo supuesto por separado; qué sí y qué no puede tocar; que muestre el plan y espere autorización; criterio de éxito; formato del informe; y que diga lo que no sabe en vez de asumir. Para entender el proyecto, usar una **auditoría de solo lectura** que cite archivo y línea y marque «NO CONFIRMADO».

## 7. Riesgos

| Riesgo | Efecto | Mitigación |
| --- | --- | --- |
| 5 V en un GPIO del ESP32-S3 | Daño permanente de la placa | Divisor o convertidor de nivel, y medir antes de conectar |
| Pines del conector que no existen | Cableado inservible | Un solo mapa, verificado contra el esquema |
| Ultrasónico propietario | Semanas perdidas | Límite de tiempo y cambio a HC-SR04 |
| Picos del motor | Reinicios y ruido en el MPU | Batería aparte, GND común y capacitor |
| Esperas bloqueantes | Muestreo irregular | Registrar `ms` y `seq`, y refactorizar después |
| Sin commits | Imposible volver atrás | Parte 0 antes de cualquier cambio |
| Pines 43 y 44 (UART0) para encoders | Cuentas falsas al arrancar | Revisar al probar; mover si hace falta |
| MTU de BLE menor al esperado | Mensajes cortados | Fragmentación o formato compacto |
| Se pierde la conexión a mitad de una sesión | Datos perdidos | `seq` para detectar el hueco y sesiones cortas |
| Documentación que contradice el código | Decisiones equivocadas | Actualizar README y marcar el estado |
| Se agrega cámara sin replantear los pines | El robot no entra en la placa | Decidir la Parte 9 antes de cablear |

## 8. Decisiones abiertas y datos que faltan

**Decisiones:**

1. ¿Cámara conectada ahora o después? (Determina si el mapa de 16 pines es válido.)
2. ¿Receptor de datos: nRF Connect, Web Bluetooth, Python, C# o USB Serial al inicio?
3. ¿Qué se hace con el ultrasónico si el protocolo no se aclara? (Propuesta: HC-SR04 genérico.)
4. ¿Se acepta el sesgo por bloqueos en los primeros datos o se hace una lectura mínima no bloqueante?
5. ¿Se usa SD como respaldo, o streaming puro?
6. ¿Criterios de aceptación numéricos de la Parte 7?

**Datos que faltan:**

- El esquema `Ultrasonic_Sensor-V1.0-SCH.pdf` (o fotos del módulo, del chip y del conector).
- Cuántos hilos son NC y a dónde va cada hilo de señal.
- La unidad de las mediciones del tester («10»).
- Si el ultrasónico es la versión con LEDs RGB o el módulo solo.
- Qué son el «puerto 100, 101 y 102».
- Cableado físico real de cada hilo, comparado con el mapa de pines.
- Tensión nominal y relación de reducción de los motores; tipo de salida del encoder.
- Pulsos por vuelta, diámetro de rueda y distancia entre ruedas.
- Tensión y tipo de batería para los motores.
- Si hay SD insertada.
- Si la carpeta de MicroPython/Pico W es solo referencia o parte del sistema.
- Con qué se ejecuta el proyecto normalmente (PlatformIO o el ejecutor de C/C++ del editor).

## 9. Orden y lista de control

**Orden recomendado:** 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7, y después 8, 9 y 10.

**Parte 0**

- ☐ Carpeta limpia y `.gitignore` actualizado
- ☐ Commit de línea base
- ☐ `Config.h` con un solo mapa y sin conflictos
- ☐ Pruebas aisladas en `test_hw/`
- ☐ ESP32 vivo por USB

**Parte 1:** ☐ MPU con Z cerca de 1 g y giroscopio cerca de 0

**Parte 2:** ☐ BLE compila ☐ Se conecta y notifica ☐ Reconexión funciona ☐ CSV guardado con `seq` y `ms`

**Parte 3:** ☐ Esquema o chip identificado ☐ Decisión de sensor tomada ☐ Distancias contra regla

**Parte 4:** ☐ Sentido correcto ☐ Cuentas por vuelta medidas ☐ Quieto sin cambios

**Parte 5:** ☐ Línea única con todos los sensores ☐ Ciclo medido

**Parte 6:** ☐ Señales verificadas ☐ Giro correcto en soporte ☐ Sin reinicios

**Parte 7:** ☐ Preguntas escritas ☐ Sesiones grabadas ☐ Análisis hecho

**Principio rector:** avanzar con cambios pequeños, medir el resultado, verificarlo y recién entonces continuar.
