# noche avances y estado del prototipo

## noche actualización del 15 de noviembre de 2026

noche la prioridad actual es diagnosticar encoders, MPU6050, único HC-SR04 frontal y luego motores, antes de modificar navegación.
noche el usuario confirma HC-SR04: hay tres comprados y solo uno conectado al frente, sin cámara ni cuchilla.
noche se preservó copia ZIP y manifiesto SHA-256 de24 archivos y se creó el entorno `diagnostico`, con fuentes separadas y las clases existentes de MPU, ultrasónico y motores.
noche se conserva el firmware original; los permisos para motores en el diagnóstico requieren confirmación física explícita de los sensores y una orden por pulso.
noche la auditoría, GPIO, comandos, carga y resultados que enviar están en [DIAGNOSTICO_HARDWARE.md](DIAGNOSTICO_HARDWARE.md); el diagnóstico exacto eléctrico sigue pendiente de mediciones.
noche el mapa activo leído el15/11 es motor D47/48/15, motor I40/42/41, encoder I39/38, encoder D44/43, MPU16/17 y HC-SR04 frontal1/2; las tablas antiguas de este registro se conservan como historia.

noche actualización del 6 de noviembre de 2026 y fecha límite de entrega del 16 de noviembre de 2026, según lo indicado por el usuario.

noche requisito confirmado para el 16: recorrer una zona delimitada por paredes o barreras detectables por el sensor de distancia, evitando obstáculos sin conducción del usuario y mediante parámetros ajustables.
noche el recorrido de 20 cm y giro es una prueba intermedia; faltan dimensiones, características de las barreras y duración de la demostración.
noche la segunda etapa será un mapa virtual con 0 para libre y 1 para obstáculos, distinguiendo además zonas desconocidas; la tercera será césped con sensores, cámara y clasificación del suelo.
noche las etapas segunda y tercera son futuras y no están implementadas.

## noche texto general de nuestra creación

noche actualización de banco del 6/11: se agregó `t` para probar derecho 3000 ms, pausa 500 ms e izquierdo 3000 ms, una sola vez y sin exigir MPU ni calibración.
noche los pulsos individuales también pasan de 800 a 3000 ms; se conservan PWM 120, parada por s/espacio/BOOT y el mapa de GPIO.
noche la consola imprime ENA/IN1/IN2 y ENB/IN3/IN4 para comparar con el cableado, sin dar por confirmado que los pines izquierdos estén mal.
noche los valores de 800 ms descritos más abajo corresponden a la versión anterior; esta actualización es la vigente y su prueba física está pendiente.

noche estamos construyendo un prototipo móvil del proyecto robot cortacésped sobre una Waveshare ESP32-S3-ETH, programado con PlatformIO y Arduino-ESP32 en C++.
noche el prototipo actual no tiene cuchilla y está en etapa de pruebas de movimiento y adquisición de datos, no de corte ni de autonomía completa.
noche los motores son Robobloq según el usuario, las ruedas tienen un diámetro informado de 6 cm y el firmware selecciona un controlador L298N.
noche la denominación exacta del motor, su tensión nominal y sus cuentas por vuelta siguen sin confirmarse documentalmente; el usuario indica que ya conoce las conexiones.

noche separamos el código en las clases `Robot`, `MotorControl`, `Sensores`, `MPU`, `Ultrasonico` y `Bluetooth`, con parámetros y GPIO en `Config.h`.
noche las pruebas actuales se ejecutan desde el mismo `main.cpp` y llaman a las clases del proyecto, para validar el código que después se integrará.
noche incorporamos conteo de encoders A/B en cuadratura x4 con interrupciones, contador de transiciones inválidas y lectura protegida mediante sección crítica.
noche agregamos una calibración manual de una vuelta por rueda para obtener cuentas por vuelta y signos, sin inventar valores del fabricante.
noche las pruebas compartidas en el chat mostraron cambios en ambos encoders, pero también transiciones inválidas, por lo que todavía no hay una calibración física aceptada.

noche el lector del MPU6050 comprueba respuestas I2C, cantidad de bytes, identidad y rangos, y devuelve error con valores inválidos cuando falla la lectura.
noche el firmware permite detectar y leer el MPU, calibrarlo quieto y observar el giro relativo integrando el eje Z del giroscopio.
noche programamos el recorrido de 20 cm por encoders, pausa de 500 ms, giro a la derecha de 90 grados estimado por el MPU y parada al terminar una sola vez.
noche el giro de 90 grados es el objetivo configurado en el código, pero su exactitud física todavía no está demostrada.

noche para destrabar las pruebas incorporamos órdenes independientes de banco: derecho adelante/atrás, izquierdo adelante/atrás y ambos adelante, con PWM 120 y pulsos de 800 ms.
noche esas órdenes muestran cuentas y errores de los encoders, usan el RGB integrado como indicador y no requieren MPU ni calibración de distancia.
noche el arranque solicita motores detenidos y las órdenes `s`, espacio o BOOT permiten solicitar una parada por software.
noche la última compilación de esas órdenes registrada en esta conversación terminó correctamente, pero cargar el firmware y observar el hardware son verificaciones distintas.
noche el problema activo es que el usuario informa que las ruedas no se mueven mientras el ESP32 está conectado por USB; todavía no contamos con la respuesta a `h` y `b`, el cambio del RGB ni mediciones de la alimentación para establecer la causa.

noche el ultrasónico tuvo lecturas fallidas y quedó desactivado por decisión del usuario, sin eliminar su clase.
noche la identificación de ese módulo y su protocolo real no está cerrada, por lo que el nombre HC-SR04 que permanece en comentarios no demuestra el modelo conectado.
noche BLE nativo, cámara, microSD y entrenamiento de modelos no están integrados en el firmware activo.
noche la carpeta de entrenamiento contiene material de referencia para otro firmware y un recolector que interpreta JSON, mientras el `main.cpp` actual emite mensajes de diagnóstico de texto.
noche el resultado hasta ahora es una base de firmware compilada con herramientas de prueba y controles de fallo, con validación física pendiente de motores, encoders, MPU y recorrido completo.

## noche evidencia del estado actual

| Área | Estado | Evidencia o límite |
|---|---|---|
| Entorno | noche CONFIGURADO | `platformio.ini:5`, `platformio.ini:8`, `platformio.ini:9`, `platformio.ini:10`: esp32s3, plataforma local, devkitc-1, Arduino |
| Puerto y USB | noche CONFIGURADO | `platformio.ini:11`, `platformio.ini:13`, `platformio.ini:16`: COM3, 115200 y USB nativo |
| Compilación | noche COMPILADO previamente | noche salida SUCCESS de la sesión anterior, duración 43,86 s; no se compiló en esta revisión documental |
| Motores | noche IMPLEMENTADO; hardware pendiente | `src/MotorControl.cpp:26`, `src/main.cpp:134`: dirección, PWM y comandos de banco |
| Encoders | noche IMPLEMENTADO; calibración pendiente | `src/Sensores.cpp:54`, `src/Sensores.cpp:80`, `src/main.cpp:96` |
| MPU | noche IMPLEMENTADO; validación integral pendiente | `src/MPU.cpp:15`, `src/MPU.cpp:39`, `src/MPU.cpp:54`, `src/MPU.cpp:79` |
| Recorrido | noche IMPLEMENTADO; no aprobado físicamente | `src/main.cpp:115`, `src/main.cpp:187`; cuentas/vuelta aún cero en `src/Config.h:76` |
| Ultrasónico | noche DESACTIVADO en main | `src/main.cpp:276`; clase TRIG/ECHO conservada en `src/Ultrasonico.cpp:30` |
| Comunicación activa | noche USB SERIAL | `src/main.cpp:275`, `src/main.cpp:283`; no llamada a `robot.bt` en main |
| Bluetooth existente | noche UART HC-05, deshabilitada | `src/Bluetooth.cpp:3`, `src/Config.h:58`; no implementación GATT BLE |
| Flujo antiguo Robot | noche EXISTE, no llamado por main | `src/Robot.cpp:3`, `src/Robot.cpp:34`; `src/main.cpp:271`, `src/main.cpp:281` |
| Git | noche SIN HISTORIAL | noche lectura actual: rama `prueba-encoders`, ningún commit y archivos sin seguimiento |
| Cuchilla | noche NO EXISTE en el prototipo | noche aclaración directa del usuario del 6 de noviembre; los textos antiguos que dicen desconectarla quedaron desactualizados |

## noche mapa activo, no certificación del cableado

| Función | GPIO | Referencia |
|---|---|---|
| Motor derecho ENA / IN1 / IN2 | 40 / 41 / 42 | `src/Config.h:21` |
| Motor izquierdo ENB / IN3 / IN4 | 47 / 48 / 15 | `src/Config.h:24` |
| Encoder izquierdo A / B | 38 / 39 | `src/Config.h:43` |
| Encoder derecho A / B | 43 / 44 | `src/Config.h:45` |
| MPU SDA / SCL | 16 / 17 | `src/Config.h:50` |
| RGB integrado | 21 | `src/Config.h:65` |
| BOOT | 0 | `src/Config.h:63` |
| TRIG / ECHO reservados, no iniciados | 1 / 2 | `src/Config.h:38`, `src/main.cpp:276` |

noche el mapa actual reserva IO21 para el RGB e IO15 para IN4, de modo que la propuesta antigua de segundo ultrasónico en IO15 no puede añadirse sin revisar el mapa.
noche la cámara permanece fuera de la configuración de prueba; la coexistencia final con todos los periféricos no está resuelta.

## noche pruebas disponibles

| Orden | Acción implementada | Resultado físico registrado |
|---|---|---|
| `h` | noche detener y mostrar menú | noche falta confirmar en la sesión actual |
| `d` / `f` | noche derecho adelante / atrás, 800 ms | noche pendiente |
| `i` / `j` | noche izquierdo adelante / atrás, 800 ms | noche pendiente |
| `b` | noche ambos adelante, 800 ms | noche usuario informa inmovilidad con USB; causa NO CONFIRMADA |
| `s` / espacio / BOOT | noche solicitar parada | noche latencia y respuesta física pendientes |
| `e` | noche leer cuentas y errores | noche hubo conteos y errores en registros previos del chat |
| `r`, una vuelta por rueda, `k` | noche medir cuentas/vuelta y signo en RAM | noche sin calibración aceptada |
| `p`, `c`, `g` | noche lectura, calibración y giro manual del MPU | noche falta cierre con evidencia del firmware actual |
| `a` | noche recorrido 20 cm y giro derecho | noche pendiente; exige cuentas/vuelta y MPU calibrado |

## noche historial de avances

| Etapa | Avance | Pendiente |
|---|---|---|
| Identificación de placa | noche fotos y pinout identificaron Waveshare ESP32-S3-ETH | noche perfil final de memoria/cámara |
| Consolidación de pines | noche mapa activo en Config, RGB21 e IN4 en15 | noche cotejo físico y arquitectura futura |
| Diagnóstico ultrasónico | noche se agregó timeout y reporte de pulso y niveles | noche identificar módulo; trabajo pausado |
| Lectura MPU | noche validación de transacciones y calibración | noche prueba física repetible |
| Encoders | noche cuadratura, errores, protección y r/k | noche conteo estable y cuentas/vuelta |
| Recorrido | noche máquina de estados 20 cm y giro | noche aceptación en piso |
| Banco de motores | noche comandos de pulsos independientes compilados | noche resolver inmovilidad reportada con USB |
| Editor | noche se detectaron dos rutas inexistentes repetidas y configuración MinGW dentro de src | noche confirmación de que desaparecieron los avisos tras regenerar IntelliSense |
| Organización actual | noche se crean registro, reglas y plan con crítica del boceto | noche acordar requisitos obligatorios de entrega |

## noche registro de la próxima prueba

| Campo | Dato a completar |
|---|---|
| Fecha, identificador del firmware y comando de carga | noche PENDIENTE |
| USB conectado, fuente del ESP32 y fuente del driver | noche PENDIENTE |
| Respuesta exacta a `h` | noche PENDIENTE |
| Respuesta exacta a `d`, `i` y `b`, por separado | noche PENDIENTE |
| RGB, rueda que gira y sentido | noche PENDIENTE |
| Tensiones antes y durante el pulso, con punto de medida | noche PENDIENTE |
| Cuentas, errores y reinicios | noche PENDIENTE |
| Resultado y siguiente submeta | noche PENDIENTE |

noche una prueba sin movimiento también aporta un resultado útil si registra qué orden recibió la placa y qué ocurrió en la salida del driver.
