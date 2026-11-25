# noche diagnóstico independiente — 15 de noviembre de 2026

## noche alcance y estado

noche hardware confirmado por el usuario: Waveshare ESP32-S3 ETH-CAM sin cámara conectada, dos motores Robobloq con encoder A/B, L298N, MPU6050 y UN HC-SR04 frontal conectado, aunque hay tres comprados.
noche el prototipo no tiene cuchilla; este firmware no contiene navegación, sensores laterales ni cálculo de resolución supuesto.
noche la causa eléctrica exacta de los errores de encoder y del anterior arranque inesperado del motor sigue NO CONFIRMADA.
noche la prueba independiente fue solicitada expresamente en esta tarea y sustituye, para este diagnóstico, la preferencia anterior por un único main de pruebas.

## noche copia y archivos

noche antes de editar se guardó `backups/antes_diagnostico_20261115_203556.zip`, con 24 archivos de fuentes, configuración y documentación, junto con su manifiesto SHA-256.
noche los archivos originales de `src/` y sus asignaciones se conservan; los cambios de firmware están en `src/diagnostico/` y en los filtros de `platformio.ini`.

| Archivo | Función |
|---|---|
| `src/diagnostico/main.cpp` | noche menú, modos exclusivos, validación explícita del usuario y pulsos individuales |
| `src/diagnostico/EncoderDiagnostico.cpp` y `.h` | noche captura simultánea del banco GPIO, contadores, matriz y cola de eventos |
| `src/diagnostico/Cuadratura.h` | noche decodificador relativo de cuadratura sin resolución supuesta |
| `src/MPU.cpp`, `src/Ultrasonico.cpp`, `src/MotorControl.cpp` | noche clases existentes reutilizadas por el entorno independiente |
| `platformio.ini:26` | noche entorno diagnostico con filtro propio; el entorno principal excluye la carpeta nueva |

## noche inspección del firmware anterior

| Evidencia | Resultado y límite |
|---|---|
| `src/Sensores.cpp:54` | noche cuadratura x4 con tabla válida, errores de salto simultáneo A/B y sección crítica; no hay Serial dentro de ISR |
| `src/Sensores.cpp:56` | noche A y B se leen sucesivamente con digitalRead; una señal puede cambiar entre ambas lecturas, pero NO se confirmó que esa sea la causa de los errores físicos |
| `src/Sensores.cpp:80` | noche INPUT_PULLUP por defecto e interrupciones CHANGE en ambos canales; no mide voltajes ni identifica tipo de salida |
| `src/Sensores.cpp:96` | noche contadores leídos con protección; no hay evidencia de variables compartidas desprotegidas en ese acceso |
| `src/main.cpp:73`, `src/Config.h:26` | noche menú y comentario conservan IN4=15, pero el valor activo es IZQ_B=41; confiar en Config, no en ese mensaje fijo |
| `src/main.cpp:43` | noche el chequeo previo de mapa no incluía el HC-SR04 inactivo; el diagnóstico incluye también TRIG, ECHO y BOOT |
| `src/MPU.cpp:15`, `src/MPU.cpp:39` | noche se comprueban transacción, cantidad de bytes, identidad y rangos; I2C100 kHz, timeout25 ms |
| `src/MPU.cpp:54` | noche calibración de500 muestras con espera2 ms, al menos1 s; rechaza giro mayor a5 grados/s, pero no prueba por sí sola horizontalidad ni ausencia de vibración |
| `src/MPU.cpp:79` | noche error de lectura produce false y NaN; escalas16384 LSB/g y131 LSB/(grado/s), coherentes con rangos comprobados |
| `src/Ultrasonico.cpp:30`, `src/Ultrasonico.cpp:61` | noche TRIG10 us, pulseIn con timeout, validez y mediana de3; el timeout no distingue desconexión de eco ausente/incompleto |
| `src/MotorControl.cpp:7` | noche arranque configura salidas y pide parada, pero el nivel físico durante reset y sin alimentación no está garantizado por ese código |
| `src/Config.h:76` | noche cuentas/vuelta todavía cero; no confundir conteos con pulsos por vuelta ni con centímetros |

noche intercambiar A y B cambia el signo relativo, pero no corrige por sí solo saltos inválidos, cableado cruzado entre ruedas o niveles eléctricos incorrectos.
noche invalidas=0 tampoco demuestra ausencia total de pérdida de pulsos: podrían perderse ciclos completos y hace falta una referencia de vueltas y repetibilidad.

## noche GPIO activos y reserva de cámara

noche la tabla siguiente copia el mapa de `src/Config.h:21`, `src/Config.h:38`, `src/Config.h:43`, `src/Config.h:50` y `src/Config.h:63`; representa asignaciones de software y no certifica continuidad física.

| GPIO | Uso actual declarado | Uso futuro cámara / restricción |
|---|---|---|
| 0 | noche BOOT, parada software | noche strapping, conservar función de arranque |
| 1 | noche TRIG frontal | noche VSYNC |
| 2 | noche ECHO frontal adaptado | noche HREF |
| 3 | noche sin asignación | noche XCLK; strapping |
| 4–7 | noche microSD interna, no iniciada | noche CS4, MISO5, MOSI6, CLK7; no cabezal lateral |
| 8 | noche control interno de cámara, no iniciado | noche ENABLE cámara; no cabezal lateral |
| 9–14 | noche W5500 interno, no iniciado | noche RST9, INT10, MOSI11, MISO12, CLK13, CS14; no cabezal lateral |
| 15 | noche DER_B / IN2 | noche D6 |
| 16 | noche MPU SDA | noche sin señal de cámara en el mapa del fabricante |
| 17 | noche MPU SCL | noche sin señal de cámara en el mapa del fabricante |
| 18 | noche sin asignación | noche D7 |
| 19 / 20 | noche USB nativo | noche reservados para comunicación USB |
| 21 | noche RGB reservado, no usado por este diagnóstico | noche RGB integrado |
| 22–25 | noche no existen como GPIO del ESP32-S3 | noche no asignar |
| 26–32 | noche interfaz de memoria, no cabezal lateral | noche no proponer para cableado externo |
| 33–37 | noche ocupados por funciones internas | noche excluidos del diagnóstico |
| 38 | noche encoder I B | noche D5 |
| 39 | noche encoder I A | noche PCLK |
| 40 | noche PWM_I / ENB | noche D4 |
| 41 | noche IZQ_B / IN4 | noche D0 |
| 42 | noche IZQ_A / IN3 | noche D3 |
| 43 | noche encoder D B | noche UART0 TX; posible actividad de arranque a comprobar |
| 44 | noche encoder D A | noche UART0 RX; no iniciar UART0 sobre él durante captura |
| 45 | noche sin asignación | noche D1; strapping |
| 46 | noche sin asignación | noche D2; strapping y tratado como entrada según guía Waveshare |
| 47 | noche PWM_D / ENA | noche SIOC |
| 48 | noche DER_A / IN1 | noche SIOD |

noche no hay duplicados en el conjunto activo; sí hay diez GPIO de este montaje compartidos con la cámara futura:1,2,15,38,39,40,41,42,47,48.
noche GPIO3,18,45,46 no tienen asignación actual, pero no son una propuesta de recableado y tienen funciones o restricciones que deben revisarse.
noche al incorporar cámara habrá que rediseñar el reparto; mantener cuatro canales rápidos de encoder y dos PWM directos no se resuelve solo desplazando señales lentas a I2C.
noche fuentes: [guía oficial de Waveshare](https://docs.waveshare.com/ESP32-S3-ETH/Development-Environment-Setup-Arduino), [esquema de la placa](https://files.waveshare.com/wiki/ESP32-S3-ETH/ESP32-S3-ETH-Schematic.pdf) y [GPIO y strapping de Espressif](https://documentation.espressif.com/projects/esp-idf/en/v5.4.3/esp32s3/api-reference/peripherals/gpio.html).
noche la guía indica flash16 MB y OPI PSRAM, mientras el perfil actual es devkitc-1 de8 MB sin PSRAM; se conserva para aislar el diagnóstico y no implica que la cámara ya esté configurada.

## noche cargar el diagnóstico

noche apagar potencia de motores para el primer ensayo, mantener encoders correctamente alimentados y conservar masa común; el fallo previo de arranque espontáneo no se considera resuelto por compilar.
noche desde la carpeta del proyecto ejecutar explícitamente el entorno diagnostico:

```powershell
pio run -e diagnostico
pio run -e diagnostico -t upload
pio device monitor -e diagnostico -p COM3 -b 115200
```

noche si `pio` no está en PATH, usar su ejecutable instalado:

```powershell
& "$env:USERPROFILE/.platformio/penv/Scripts/platformio.exe" run -e diagnostico -t upload
```

noche se espera el identificador `DIAG-S3-20261115-v1`, fecha de compilación y reset_reason al conectar USB; `h` muestra ayuda y GPIO efectivos.
noche para volver al firmware anterior se puede cargar `pio run -e esp32s3 -t upload`, o restaurar selectivamente desde la copia; ambos reemplazan el programa de la placa y requieren tu decisión.

## noche 1 — encoders manuales, primera prueba

- noche enviar `e` y después `r` con ruedas quietas; la captura inicial usa INPUT_PULLUP, igual que el lector anterior.
- noche observar60 s en reposo y guardar el resumen: cuentas, cambios, invalidas y log_perdidos deben permanecer sin nuevos cambios.
- noche girar solo la izquierda una vuelta marcada y lentamente hacia adelante; enviar `q`, guardar matriz y repetir a la inversa.
- noche enviar `r` y repetir para la derecha, dejando la otra rueda quieta.
- noche repetir cinco vueltas individuales por lado/sentido para medir dispersión, sin copiar números a Config todavía.
- noche mandar `l` para apagar la traza detallada si el envío es excesivo; los contadores siguen activos, y `l` vuelve a mostrarla.
- noche cambiar pull-up con `p` solo tras confirmar tipo de salida y tensiones compatibles, con ruedas quietas; la captura se reinicia y se invalida la confirmación anterior.
- noche conservar la misma alimentación y velocidad manual al comparar INPUT con INPUT_PULLUP; mejora con pull-up no demuestra por sí sola colector abierto.

| Campo | Qué significa |
|---|---|
| `AB=01` | noche nivel A0, B1 en el resumen |
| `EDGE ... AB=00>01 paso=1` | noche transición observada con marca micros; positivo es la convención00→01→11→10→00 |
| `irq=IA` | noche callback que produjo la captura; no garantiza que solo ese canal cambiara antes de atenderlo |
| `rise`, `fall`, `cambios` | noche flancos observados de cada canal; rise se puede usar como pulsos observados, sin asumir resolución |
| `+=`, `-=` | noche pasos válidos en cada sentido relativo; físicamente adelante se debe anotar |
| `invalidas` | noche ambos bits cambiaron entre dos capturas; puede ser pérdida de atención, ruido o señales incompatibles |
| `sin_cambio` | noche callback atendido sin cambio nuevo en su rueda; no equivale automáticamente a rebote eléctrico |
| `log_perdidos` | noche eventos descartados por cola llena; cuentas siguen, pero la traza deja de ser completa |
| `MATRIZ` | noche cantidades desde cada AB hacia00/01/10/11; no es porcentaje de tiempo en cada estado |

noche una cola de255 eventos útiles no es un analizador lógico: bajo carga puede saturarse y la lectura simultánea no recupera eventos que nunca llegaron a atenderse.
noche no se aplica debounce ni filtro temporal para evitar esconder transiciones antes de conocer la causa.

| Patrón observado | Hipótesis a distinguir, NO diagnóstico definitivo |
|---|---|
| noche cambia A pero nunca B | noche canal desconectado, señal fija, asignación, salida o captura |
| noche cambios con ruedas quietas | noche ruido, referencia de masa, contacto o entrada flotante |
| noche cambian ambas ruedas al mover una | noche cruce de señales, acoplamiento o movimiento mecánico real |
| noche manual lento limpio y rápido con invalidas | noche límite de atención, integridad de señal o flancos deficientes |
| noche manual limpio y motor con errores | noche interferencia o alimentación bajo carga; comparar velocidades equivalentes |
| noche traza llena sin invalidas | noche límite del registro; repetir con traza apagada y rueda lenta |

noche medir alimentación del encoder y máximos/mínimos de A/B respecto de GND; un tester puede comprobar niveles estáticos, pero flancos, picos y fase requieren osciloscopio o analizador con niveles compatibles.
noche verificar cableado, continuidad sin alimentación, longitud, conectores y separación de potencia sin recablear por ensayo arbitrario.
noche el pull-up interno no adapta5 V a3,3 V y la compatibilidad del encoder con alimentación3,3 V sigue NO CONFIRMADA hasta conocer su especificación o medir correctamente.

## noche 2 — MPU6050

noche enviar `m`: muestra inicio VALIDO o FALLO_I2C_IDENTIDAD_O_RANGO y comienza muestras cada200 ms en ese modo.
noche enviar `c` manteniendo robot quieto/horizontal, esperar el resultado y guardar aceleración en g y velocidad angular en grados/s.
noche en reposo horizontal se espera aproximadamente gravedad en un eje y giro cercano a cero tras calibrar; anotar orientación y deriva durante60 s, sin exigir ceros exactos.
noche girar manualmente y comprobar respuesta de cada eje; comparaciones físicas de ángulo se harán después de validar las lecturas.
noche un fallo imprime INVALIDO y descarta los valores; `m` reintenta, y la calibración vuelve a ser necesaria.
noche no se hacen cortes o cambios de cableado en caliente como parte de este procedimiento; las pruebas de desconexión física se preparan sin potencia y se vuelve a iniciar.

## noche 3 — HC-SR04 frontal único

noche antes de `u`, comprobar alimentación5 V, masa común y adaptación de ECHO; GPIO2 no debe recibir directamente la salida de5 V.
noche el circuito de adaptación real y los valores actuales deben informarse; no se modificaron conexiones ni resistencias durante esta tarea.

```text
ECHO ---- R superior ----+---- GPIO2
                        |
                     R inferior
                        |
                       GND
```

noche la ecuación ideal es `Vgpio = Vecho × R inferior / (R superior + R inferior)`; con1 kΩ arriba y2,2 kΩ abajo resulta3,4375 V si ECHO alcanza5 V, por lo que no corresponde llamarlo exactamente3,3 V.
noche un ejemplo a evaluar antes de cambiar el circuito es2,2 kΩ arriba y3,3 kΩ abajo:3,0 V nominales para ECHO5 V; hay que comprobar tolerancias, tensión real y nivel alto reconocido.
noche referencias eléctricas: [hoja ESP32-S3](https://documentation.espressif.com/esp32-s3_datasheet_en.pdf) y [hoja HC-SR04 de Elecfreaks](https://www.digikey.com/htmldatasheets/production/3822706/0/0/1/hc-sr04.pdf).
noche enviar `u` inicia únicamente el frontal TRIG1/ECHO2, con una medición aproximadamente cada200 ms y timeout configurado de12600 us para máximo200 cm.
noche la hoja del módulo recomienda separación mayor de60 ms; la cadencia del diagnóstico deja margen y no activa los otros dos sensores comprados.
noche se informa pulso, distancia cruda fraccional, distancia filtrada entera, niveles ECHO antes/después, duración y estado de validez.
noche medir objetos planos a20,50 y100 cm contra una regla, guardar al menos30 lecturas por distancia y registrar media, desviación muestral, mínimo/máximo y número de inválidas.
noche `u` reinicia estadísticas al cambiar de distancia; la dispersión solo tiene sentido con objeto y robot fijos.
noche timeout o fuera de rango producen distancia inválida, no camino libre; timeout no demuestra fallo de hardware por sí solo.

## noche 4 — confirmaciones y motores

noche solo después de revisar físicamente cada prueba, enviar `1` para confirmar encoders, `2` MPU y `3` ultrasónico; son declaraciones del usuario y comprobaciones mínimas del software, no aprobación automática.
noche `1` exige actividad de ambas ruedas sin invalidas ni pérdidas de registro, `2` exige lectura y calibración MPU válidas, y `3` exige al menos10 lecturas válidas y última lectura válida.
noche no confirmar con esos comandos si fallan las mediciones, niveles o repetibilidad, aunque el software acepte los contadores.
noche con ruedas levantadas y el problema de arranque inesperado investigado, alimentar la potencia del driver, enviar `v` y después un solo comando `d`, `f`, `i` o `j`.
noche cada `v` habilita un único pulso independiente de hasta3000 ms a PWM120; no existe orden para ambos ni secuencia automática en este entorno.
noche repetir `v` antes de cada nuevo pulso y respetar la pausa mínima500 ms.
noche comprobar rueda física, sentido real y cambio de su encoder; anotar también si cambia el encoder del lado que debería estar quieto.
noche `s`, espacio, BOOT, desconexión USB detectada, errores de encoder, saturación del registro, atraso de loop o ausencia total de pasos tras1,2 s solicitan parada.
noche la parada sigue siendo software y no resuelve estados eléctricos durante reset, CPU bloqueada o alimentación incorrecta; si arranca sin orden, apagar potencia y volver al diagnóstico eléctrico.
noche durante motor solo se consultan encoders, para no introducir pulseIn ni calibración bloqueante en esa prueba.

## noche MCP23017 y cámara futura

noche el [MCP23017](https://www.microchip.com/en-us/product/mcp23017) ofrece16 E/S por I2C; se estudiaría para LED externos, botones y señales de configuración lentas, con pull-ups del bus compatibles y dirección distinta del MPU.
noche no incorpora un generador PWM para sustituir ENA/ENB ni un contador de cuadratura que garantice capturar los flancos rápidos; su interrupción no convierte el bus I2C en un registro ilimitado de eventos.
noche ECHO temporizado, cámara paralela y sus relojes permanecen fuera de esa propuesta de expansión.
noche llevar direcciones del L298N al expansor requeriría controlar habilitación y fallos de I2C; perder comunicación puede dejar la última salida retenida, por lo que no se propone como arreglo inmediato del arranque inesperado.
noche la futura cámara ocupa14 señales del cabezal más ENABLE8 interno; quedan pocos GPIO y el MCP no demuestra por sí solo que alcance el presupuesto de PWM y encoders.
noche consultar la [hoja del MCP23017](https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP23017-MCP23S17-16-Bit-IO-Expander-with-Serial-Interface-DS20001952.pdf) antes de definir expansión; no se agrega biblioteca ni asignación nueva ahora.

## noche navegación experimental futura — propuesta, no implementada

noche estados propuestos: ESPERA → AVANCE → PARADA_POR_OBSTACULO → GIRO_CONTROLADO → ASENTAMIENTO → NUEVA_MEDIDA_FRONTAL → DECISION, con FALLO y parada como salidas explícitas.
noche medir el frente después de girar da una observación nueva en otra orientación; no ofrece distancias laterales simultáneas ni detecta todo el espacio barrido al girar.
noche giro, prioridad izquierda/derecha, margen de frenado, reintentos y criterio de desbloqueo se definirán después de calibrar motores/encoders/MPU y validar el frontal.
noche la maniobra de exploración deberá tener ángulo y tiempo máximos, comprobar lectura fresca y parar ante dato inválido; un sensor frontal tampoco garantiza despeje trasero al retroceder.
noche ninguna de estas transiciones se activa en el diagnóstico y no hay garantía de cobertura total de la zona sin validación física.

## noche qué enviar primero

- noche identificación DIAG, PINES y descripción de alimentación y niveles medidos de encoders/ECHO.
- noche resumen tras60 s quieto, diez a veinte líneas EDGE por rueda lenta y resultado de `q` al terminar cada vuelta marcada.
- noche indicar qué rueda y sentido físico corresponden a cada registro, modo INPUT/PULLUP y si log_perdidos fue cero.
- noche después enviar inicio/calibración y muestras MPU, y las estadísticas del único HC-SR04 a distancias conocidas.
- noche mantener todas las pruebas físicas como PENDIENTES hasta ver sus resultados, sin avanzar a navegación por el solo hecho de compilar.

## noche verificación de software y límites

noche se comprobó la integridad del ZIP y mediante hashes que las fuentes originales de src anteriores al diagnóstico no se modificaron.
noche ambos entornos compilaron separados; la versión final del diagnóstico, incluidos inicialización y buffer serie, terminó SUCCESS en37,13 s.
noche se ejecutó una simulación C++ de los archivos reales del diagnóstico con GPIO, reloj, USB y sensores simulados en una carpeta temporal externa al proyecto.
noche pasaron las16 combinaciones de cuadratura, ambos canales, inversión, salto inválido, saturación y reset del registro, bloqueo previo a confirmaciones, duración del pulso y paradas por comando, USB, BOOT, atraso y error de encoder, además de invalidación MPU/ultrasónico.
noche esa simulación verifica decisiones de software, no tiempos de interrupción reales, calidad de señales, motores ni exactitud de sensores.
noche se reserva un buffer TX de8192 bytes para menú y matrices, sin espera de transmisión durante movimiento; si faltan líneas hay que repetir con traza apagada, porque log_perdidos mide cola de eventos y no todas las posibles pérdidas del receptor USB.
noche no se cargó firmware ni se hicieron movimientos físicos desde las herramientas del asistente.
noche el usuario seleccionó «otra configuración» para alimentación/adaptación y todavía debe describirla; no se considera confirmada la compatibilidad eléctrica de A/B ni ECHO.
