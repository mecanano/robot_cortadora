# noche plan de cierre al 16 de noviembre de 2026

noche revisión del 6 de noviembre de 2026 basada en el código actual, el boceto agregado y los resultados relatados en el chat.
noche objetivo obligatorio confirmado por el usuario: que el prototipo se mueva autónomamente para el 16 de noviembre, sin cuchilla.
noche el recorrido de 20 cm y giro de 90 grados es una prueba intermedia de control, no la definición completa de autonomía.
noche este plan agrega prioridades, fechas objetivo y criterios propuestos; los valores de aceptación que no provienen del código están identificados como PROPUESTA.
noche escenario confirmado: recorrer una zona delimitada por paredes o barreras detectables por distancia, evitando obstáculos sin conducción del usuario.
noche faltan dimensiones, materiales y altura de barreras, obstáculos de prueba y duración; el reconocimiento de césped queda para una etapa posterior.

## noche etapas de nuestra creación

| Etapa | Alcance confirmado por el usuario | Relación con la entrega |
|---|---|---|
| 1 | noche recorrer una zona delimitada, evitar obstáculos y decidir movimientos mediante parámetros sin conducción manual | noche objetivo del 16/11 |
| 2 | noche construir un mapa virtual de coordenadas: 0 para zona recorrible y 1 para obstáculos | noche posterior a validar la etapa 1 |
| 3 | noche trabajar sobre césped coordinando cámara y sensores, clasificación básica de suelo y planificación del recorrido alrededor de objetos | noche visión futura, sin compromiso para el 16 |

noche la tercera etapa contempla en el futuro decisiones de corte, pero el prototipo actual sigue sin cuchilla y esta planificación no incorpora un sistema de corte.
noche para la segunda etapa también habrá que representar las celdas desconocidas, por ejemplo con un estado adicional; no se deben marcar como libres las zonas que nunca se observaron.
noche el tamaño de celda, origen, orientación, localización, deriva y proyección de las mediciones son decisiones futuras, no funciones disponibles hoy.

## noche aceptación propuesta para la primera etapa

- noche un inicio deliberado habilita la marcha; después el usuario no envía órdenes para cada movimiento.
- noche el robot detecta los obstáculos del ensayo, decide una maniobra y retoma el recorrido sin colisionar ni salir de la zona.
- noche un sensor inválido, falta de progreso o imposibilidad de resolver una maniobra provoca una parada explícita, en lugar de avanzar con datos inventados.
- noche los parámetros a definir incluyen velocidad de avance/giro, distancia de detección, margen de parada, ángulo de maniobra, máximos de tiempo y reintentos, y duración o condición de fin.
- noche esos umbrales se ajustan con mediciones del montaje y no se presentan todavía como valores validados.
- noche eficiencia en esta etapa significa medir tiempo detenido, repeticiones de maniobras y bloqueos; comparar cambios sobre el mismo circuito y alimentación.
- noche evitar obstáculos no demuestra cobertura completa ni una ruta óptima, por lo que esas capacidades no se dan por terminadas sin una forma de medirlas.
- noche el límite será físico: paredes o barreras detectables por distancia, sin requerir detección de líneas ni límites virtuales en esta etapa.
noche se debe comprobar que el sensor detecta las barreras reales a la altura de montaje y en esquinas y aproximaciones oblicuas; detectar una pared de frente no demuestra cobertura lateral ni trasera.
noche si el sensor no distingue barrera de obstáculo, ambos se tratan como zona no transitable; no hace falta clasificarlos para esta primera etapa.
- noche se propone una prueba con al menos tres disposiciones de obstáculos y tres ejecuciones por disposición, registrando duración, intervenciones, colisiones, salidas y fallos; duración y dimensiones aún por acordar.

## noche fechas y dependencias

| Meta | Fecha objetivo propuesta | Resultado de cierre | Estado al 6/11 |
|---|---|---|---|
| 1 | 6/11 | noche alcance de autonomía y firmware identificados | noche documentación creada; conducta y barreras definidas; aceptación pendiente |
| 2 | 6–7/11 | noche ambos motores responden de forma repetible con USB | noche BLOQUEO ACTIVO |
| 3 | 8/11 | noche encoders estables y cuentas/vuelta medidas | noche pendiente |
| 4 | 9/11 | noche MPU estable y sentido de giro verificado | noche pendiente |
| 5 | 10/11 | noche percepción y límites necesarios para la autonomía validados | noche sensor/protocolo y entorno pendientes |
| 6 | 11–12/11 | noche control autónomo integrado en el firmware real | noche no implementado en el main actual |
| 7 | 13–14/11 | noche pruebas integrales, repeticiones y datos de evidencia | noche pendiente |
| 8 | 15–16/11 | noche versión congelada, demostración y documentación final | noche pendiente |

noche el camino de integración es 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8; identificar el sensor puede avanzar durante las pruebas de motores.
noche el 15 queda reservado para corregir defectos de la versión elegida y ensayar, sin introducir funciones nuevas.
noche una fecha en la tabla es un compromiso de planificación propuesto, no evidencia de que la tarea esté terminada.

## noche 1 — definir y conservar la base

- [ ] noche **1.a** describir en una frase la demostración autónoma: entorno, tarea, inicio, final y situaciones que debe resolver.
- [ ] noche **1.b** fijar cuáles sensores son obligatorios para esa demostración y cuáles pueden quedar fuera sin incumplirla.
- [ ] noche **1.c** cargar el firmware de banco actual, enviar `h` y guardar menú y fecha de carga para identificar qué corre en la placa.
- [ ] noche **1.d** cotejar el cableado con el mapa de `AVANCES.md`, sin cambiar conexiones que ya estén correctas.
- [ ] noche **1.e** registrar fuentes, tensiones nominales, GND común y posición de los jumpers del driver, sin atribuir el fallo USB a una causa no medida.
- [ ] noche **1.f** revisar el conjunto de archivos y preparar una línea base de Git sin incluir cachés ni referencias ajenas por accidente.
- [ ] noche **1.g** crear el primer commit cuando se ejecute la tarea de versionado, sin renombrar ramas como requisito innecesario.
- [x] noche **1.h** separar avances, reglas y plan; conservar el boceto y señalar sus contradicciones.

noche cierre de meta 1: escenario y aceptación escritos, firmware identificado y una base recuperable.

## noche 2 — cerrar el problema actual de motores

- [ ] noche **2.a** conectar USB, abrir exclusivamente COM3 a 115200 y guardar la respuesta a `h`.
- [ ] noche **2.b** enviar `d` una vez y registrar mensaje BANCO, LED azul, rueda que gira y sentido.
- [ ] noche **2.c** esperar la pausa indicada y repetir con `f` para el sentido contrario del derecho.
- [ ] noche **2.d** repetir por separado con `i` y `j` para el izquierdo, con LED magenta.
- [ ] noche **2.e** probar `b` para ambos y registrar LED blanco, cuentas, errores y posibles reinicios.
- [ ] noche **2.f** si no aparece BANCO, resolver recepción de comandos, puerto y firmware antes de atribuir el problema al motor.
- [ ] noche **2.g** si aparece BANCO pero no gira, medir alimentación del driver y sus entradas durante el pulso, comparando con el mapa activo.
- [ ] noche **2.h** comparar una condición por vez entre USB conectado y la alimentación alternativa real, anotando exactamente qué fuentes y masas cambian.
- [ ] noche **2.i** comprobar `s`, espacio y BOOT durante pulsos, y que una orden nueva no invierta directamente un motor en movimiento.
- [ ] noche **2.j** repetir tres veces cada sentido y ambos motores, como PROPUESTA de repetibilidad mínima.

noche cierre de meta 2: ambos lados giran según la orden, paran al finalizar y no hay reinicios en esas repeticiones con el montaje documentado.
noche los 800 ms y PWM 120 son parámetros de diagnóstico, no una garantía de arranque ni de distancia (`src/Config.h:68`).

## noche 3 — convertir pulsos en distancia confiable

- [ ] noche **3.a** observar `e` con ruedas quietas durante 60 segundos y guardar cuentas/errores iniciales y finales.
- [ ] noche **3.b** usar `r`, girar cada rueda una vuelta completa hacia adelante y enviar `k`.
- [ ] noche **3.c** si se rechaza la calibración, registrar por separado cuentas y errores de cada lado y resolver la causa antes de copiar valores.
- [ ] noche **3.d** repetir cinco mediciones manuales por rueda, registrando sentido y marca de vuelta, como PROPUESTA de comprobación.
- [ ] noche **3.e** comprobar que girar la izquierda no modifica la derecha y viceversa.
- [ ] noche **3.f** comprobar signos al retroceder y comparar conteo a velocidad manual baja y durante el pulso de motor.
- [ ] noche **3.g** elegir cuentas/vuelta solo tras tener mediciones consistentes y guardar valores y signos en Config cuando estén aprobados.
- [ ] noche **3.h** medir con regla un desplazamiento de referencia y contrastar la conversión, incluyendo el diámetro efectivo y el patinamiento.

noche cierre de meta 3: cero transiciones inválidas en las pruebas que habilitan el recorrido, conteo quieto estable y cuentas/vuelta repetibles.
noche la dispersión máxima admisible de las vueltas debe acordarse tras ver la resolución; no se inventará un número de cuentas ni se ocultarán errores para habilitar `a`.

## noche 4 — cerrar lectura y giro con MPU

- [ ] noche **4.a** usar `p`, guardar aceleración y giro en reposo y verificar que responde el dispositivo esperado.
- [ ] noche **4.b** usar `c` quieto y horizontal y registrar aceptación o error.
- [ ] noche **4.c** usar `g` y girar manualmente a la derecha para verificar el signo del ángulo.
- [ ] noche **4.d** registrar 60 segundos en reposo, antes y después de activar motores, para medir deriva y vibración.
- [ ] noche **4.e** comparar giros manuales de referencia con una escuadra o marcas del piso.
- [ ] noche **4.f** verificar que un fallo de lectura informado invalida el dato y detiene el recorrido, primero en condiciones controladas.
- [ ] noche **4.g** definir un error angular aceptable para la demostración a partir de la medición y el entorno.

noche cierre de meta 4: lecturas válidas y repetibles, calibración aceptada, derecha con signo correcto y deriva cuantificada.
noche integrar `gz` da un giro relativo con deriva, no una posición absoluta ni un reconocimiento de límites.

## noche 5 — resolver percepción y límites de la autonomía

- [ ] noche **5.a** confirmar el escenario de entrega y qué debe suceder frente a obstáculo, borde o sensor inválido.
- [ ] noche **5.b** inventariar los sensores realmente disponibles con modelo y protocolo confirmado; la marca Robobloq por sí sola no define el protocolo.
- [ ] noche **5.c** si se requiere evasión, identificar y validar el sensor de distancia sin reutilizar a ciegas el código TRIG/ECHO para un módulo desconocido.
- [ ] noche **5.d** establecer una decisión de sensor el 8/11 como fecha propuesta, para dejar tiempo de integración antes del 10.
- [ ] noche **5.e** verificar lectura con distancias conocidas, ausencia de objeto, superficies y ángulos del escenario real.
- [ ] noche **5.f** definir antigüedad máxima del dato y acción ante lectura inválida; falta de eco no demuestra camino libre.
- [ ] noche **5.g** si se exige detectar límites del césped o desniveles, demostrar qué sensor los reconoce; encoders y MPU no constituyen por sí solos esa detección.
- [ ] noche **5.h** revisar la asignación de pines antes de añadir un segundo sensor, cámara o expansor.

noche cierre de meta 5: entradas suficientes para las decisiones de la autonomía elegida y comportamiento verificable ante dato inválido.
noche elegir un módulo sustituto o una arquitectura adicional exige avisar al usuario y confirmar disponibilidad; este documento no da por comprado ni conectado ningún componente.

## noche 6 — integrar movimiento autónomo

- [ ] noche **6.a** aprobar primero la prueba `a`: 20 cm, pausa y giro derecho, midiendo distancia y ángulo físicos.
- [ ] noche **6.b** escribir una tabla de estados según el escenario: espera, inicio, avance, decisión, maniobra, final y fallo.
- [ ] noche **6.c** definir el inicio autorizado y el criterio de fin; autonomía significa que no hay que enviar órdenes para cada movimiento.
- [ ] noche **6.d** usar las clases reales desde main y una sola lógica activa, sin activar por accidente el antiguo `Robot::loopPrincipal()`.
- [ ] noche **6.e** implementar la secuencia o evasión requerida con transiciones temporizadas y sensores validados, sin ciclos de espera prolongados.
- [ ] noche **6.f** conservar parada, timeouts y fallos explícitos, definiendo también qué ocurre si se pierde el enlace de diagnóstico.
- [ ] noche **6.g** probar cada transición por separado y después la secuencia completa.
- [ ] noche **6.h** verificar que no queda esperando USB ni órdenes por tramo durante la demostración autónoma.
- [ ] noche **6.i** reiniciar y comprobar que no empieza a moverse accidentalmente; un inicio deliberado es compatible con marcha autónoma posterior.

noche cierre de meta 6: el prototipo ejecuta la tarea acordada sin conducción manual durante la marcha y resuelve las condiciones de fallo definidas.
noche una secuencia prefijada sola no satisface esta entrega; se debe responder a obstáculos y barreras reales durante la marcha.

## noche 7 — repetir, medir y guardar evidencia

- [ ] noche **7.a** definir un formato de registro único, con versión, tiempo, secuencia, estado, cuentas, errores, MPU y validez de sensores presentes.
- [ ] noche **7.b** elegir un receptor que guarde ese formato y comprobar que no descarta líneas silenciosamente.
- [ ] noche **7.c** si BLE es obligatorio, implementar y medir conexión, tamaño de mensajes, pérdida y reconexión sin cambiar simultáneamente el control de movimiento.
- [ ] noche **7.d** guardar al menos tres ejecuciones completas de la demostración, como PROPUESTA inicial, con medidas físicas y resultado de cada una.
- [ ] noche **7.e** repetir con la alimentación y superficie previstas para el 16, incluyendo el caso USB que hoy falla.
- [ ] noche **7.f** probar arranque, parada, sensor inválido, falta de progreso y fin de tarea sin que el robot reanude solo una maniobra fallida.
- [ ] noche **7.g** clasificar defectos encontrados por impacto y cerrar primero los que impiden el movimiento autónomo requerido.

noche cierre de meta 7: pruebas reproducibles con resultados guardados y tolerancias explícitas, sin confundir compilación con demostración.

## noche 8 — preparar la entrega

- [ ] noche **8.a** congelar el firmware elegido el 15/11 y guardar su identificador, configuración, mapa y procedimiento de carga.
- [ ] noche **8.b** preparar una hoja breve de encendido, inicio autónomo, parada y recuperación.
- [ ] noche **8.c** ensayar la demostración completa con la misma alimentación, espacio y sensores de la entrega.
- [ ] noche **8.d** actualizar AVANCES con lo realmente demostrado y lo pendiente, sin presentar características futuras como terminadas.
- [ ] noche **8.e** conservar código, registros y documentación en una copia recuperable.
- [ ] noche **8.f** ejecutar y registrar la demostración final el 16/11.

## noche crítica del boceto original, de mayor a menor impacto

noche las referencias B indican líneas del boceto original antes de añadir el aviso de revisión; buscar también el título citado porque la numeración puede desplazarse.
noche los hallazgos siguientes separan contradicciones comprobables, omisiones del plan y afirmaciones técnicas NO CONFIRMADAS; una revisión estática no descubre todas las fallas físicas.

| Prioridad | Hallazgo y evidencia | Consecuencia para el plan |
|---|---|---|
| 1 | noche el alcance del boceto excluye navegación autónoma (B27), pero el usuario exige movimiento autónomo el 16 | noche hay que planificar autonomía y su aceptación, no cerrar solo recolección |
| 2 | noche faltan escenario, fin de tarea, límites y respuesta a obstáculos; el main actual solo hace un recorrido al recibir `a` (`src/main.cpp:115`) | noche no se puede certificar autonomía útil con el recorrido aislado |
| 3 | noche el mapa propuesto usa IN4 en21 y segundo sensor en15 (B109–117), pero Config usa RGB21 e IN4 en15 (`src/Config.h:26`, `src/Config.h:65`) | noche aplicar el boceto literalmente reintroduciría conflictos |
| 4 | noche el problema de inmovilidad con USB no figura como bloqueo con protocolo de evidencia | noche falta cerrar lo básico antes de integrar más funciones |
| 5 | noche BLE aparece en presente como modo de datos (B21), aunque `src/Bluetooth.cpp:3` usa UART y main no llama esa clase | noche es una propuesta pendiente, no una capacidad existente |
| 6 | noche el boceto depende de identificar un ultrasónico cuyo protocolo no conoce (B394–399) | noche la percepción requerida necesita una fecha de decisión y una alternativa confirmada |
| 7 | noche los motores quedan condicionados a completar sensores y BLE (B604) | noche esa dependencia no es necesaria para el diagnóstico de banco y retrasa el bloqueo activo |
| 8 | noche se proponen mains paralelos en test_hw (B203–219) | noche contradice la decisión del usuario de probar funciones reales desde main |
| 9 | noche el ejemplo MPU lee sin comprobar longitud ni todas las transacciones (B270–287) | noche es menos robusto que `src/MPU.cpp:15` y no debe sustituirlo |
| 10 | noche se afirma que leerMPU no detecta desconexión (B56, B744), pero la lectura actual comprueba el bus y devuelve error (`src/MPU.cpp:15`, `src/Sensores.cpp:37`) | noche ese diagnóstico quedó desactualizado |
| 11 | noche se afirma que no hubo pruebas físicas de encoder (B525), pero el chat contiene conteos y errores de ambos lados | noche hay evidencia parcial, aunque no aprobación de cuentas/vuelta |
| 12 | noche se propone aceptar errores de transición «0 o muy cerca» (B570), pero el recorrido rechaza cualquiera (`src/main.cpp:213`) | noche el criterio de prueba y el firmware no coinciden |
| 13 | noche el boceto atribuye motores a GPIO5–10 (B50); esos valores solo quedan en la rama IBT inactiva (`src/Config.h:13`, `src/Config.h:30`) | noche confunde configuración activa con alternativa futura |
| 14 | noche el ensayo de motores de900/1000 ms citado (B621) ya no corresponde: hoy usa800 ms y pausa mínima500 (`src/Config.h:69`) | noche seguir ese procedimiento produce expectativas incorrectas |
| 15 | noche el boceto describe CSV activo (B46), pero main emite texto por estado (`src/main.cpp:256`) | noche no hay aún un esquema de datos estable para el recolector |
| 16 | noche el recolector llama json.loads (`entrenamiento_beta_de_la camara/files/robot_ia_suelo_completo/robot_ia_suelo/entrenamiento/recolectar_datos.py:101`) | noche no acepta automáticamente los mensajes actuales ni el CSV propuesto |
| 17 | noche no hay commits y el boceto incluye `git checkout .` como vuelta atrás (B211) | noche se podría descartar trabajo seguido por Git; ese comando no recupera archivos sin seguimiento |
| 18 | noche quitar ZIP y referencias, renombrar ramas y crear entornos se mezcla con el diagnóstico de hardware (B173–219) | noche son tareas independientes, no requisitos para que un motor gire |
| 19 | noche el texto deduce I2C de encontrar una dirección (B459) | noche un ACK no identifica inequívocamente el módulo ni sus comandos; el protocolo sigue requiriendo evidencia |
| 20 | noche se propone detectar actividad sondeando durante2 s (B441) | noche puede perder pulsos rápidos y no demuestra el protocolo; tampoco debe incorporarse al control en marcha |
| 21 | noche el boceto reserva38–41 para investigar el ultrasónico (B423), pines hoy usados por encoders y motor (`src/Config.h:22`, `src/Config.h:43`) | noche el ejemplo no se puede ejecutar conectado al montaje actual sin revisar incompatibilidades |
| 22 | noche divisor y convertidor de nivel se prescriben para señales todavía desconocidas (B409–415) | noche no corresponde universalizar el circuito sin identificar dirección, amplitud y tipo de señal |
| 23 | noche la propuesta de unir ECHO con diodos (B504) no tiene circuito ni validación | noche es una alternativa NO CONFIRMADA y añade una variable innecesaria al plazo |
| 24 | noche la alimentación del motor, su reducción y salida del encoder siguen supuestas (B510) | noche no convertir la apariencia o la marca en especificación eléctrica |
| 25 | noche las cifras de caída y corriente del L298N se presentan como valores generales sin condiciones del módulo (B122) | noche falta medir carga y alimentación y consultar el componente antes de dimensionar |
| 26 | noche «tensiones altas» en PoE y arquitectura futura aparecen como hechos sin distinguir placa, módulo y conexión (B87) | noche son afirmaciones de hardware NO CONFIRMADAS en esta revisión del código |
| 27 | noche el porcentaje de muestras «sin salto» del95% no define claramente denominador ni reinicios (B681) | noche falta definir pérdidas/esperadas y cómo separar sesiones |
| 28 | noche la deriva se describe como pendiente de gx/gy/gz (B676) | noche conviene distinguir sesgo de velocidad angular, deriva del ángulo integrado y variación temporal del sesgo |
| 29 | noche propiciar streaming sin SD no resuelve desconexiones ni registro en el receptor (B21–25) | noche faltan identificación de sesión, detección de reinicio y tratamiento de pérdida |
| 30 | noche la tabla de bloqueos mezcla Robot antiguo con main actual (B729–739) | noche `Robot::evadirObstaculo` sí bloquea, pero no está llamado por el main de prueba |
| 31 | noche Nano y UART se recomiendan antes de medir requisitos de cámara, tasas y conteo (B714–723) | noche falta presupuesto de procesamiento, niveles y protocolo; no está aprobada esa arquitectura |
| 32 | noche los criterios de éxito tienen marcas de confirmado aunque son metas pendientes (B213–217 y siguientes) | noche no marcar una condición futura como prueba superada |

## noche límites y fallas potenciales del firmware actual

| Impacto | Hallazgo de revisión | Estado |
|---|---|---|
| Alto | noche main no implementa decisión autónoma continua ni evasión activa; ultrasónico omitido (`src/main.cpp:276`) | noche CONFIRMADO por lectura |
| Alto | noche los pulsos de banco no se detienen por errores de encoder ni validan MPU (`src/main.cpp:187`) | noche comportamiento de diagnóstico intencional, no control autónomo |
| Alto | noche la parada por BOOT y por plazo depende de ejecutar loop (`src/main.cpp:281`) | noche no garantiza respuesta si el procesador se bloquea; latencia física NO CONFIRMADA |
| Alto | noche el arranque configura salidas antes de llamar detener (`src/MotorControl.cpp:7`) | noche estado de las entradas del driver durante encendido/reset NO CONFIRMADO |
| Alto | noche el mapa estático comprueba duplicados, USB y33–37, pero no certifica todos los pines expuestos ni incluye BOOT (`src/main.cpp:27`) | noche comprobación parcial, no validación universal del hardware |
| Alto | noche el flujo antiguo de Robot puede mover por distancia y bloquear1,8 s en evasión (`src/Robot.cpp:20`) | noche actualmente inactivo; no activarlo como atajo a la autonomía |
| Medio | noche counts/vuelta siguen cero y k guarda en RAM (`src/Config.h:76`, `src/main.cpp:96`) | noche el recorrido no puede aprobarse sin calibración y conservación de resultados |
| Medio | noche k valida conteos mínimos, no certifica físicamente una vuelta completa (`src/main.cpp:98`) | noche necesita referencia manual y repetición |
| Medio | noche gyro limitado a rango verificado pero calibración solo rechaza giro mayor a5 grados/s (`src/MPU.cpp:61`) | noche no demuestra horizontalidad ni ausencia de aceleración/vibración |
| Medio | noche la lectura MPU no comprueba en cada muestra identidad, saturación ni datos congelados (`src/MPU.cpp:28`) | noche un bus exitoso no garantiza toda la calidad de la medición |
| Medio | noche digitalRead A y B son lecturas sucesivas y el conteo es por interrupciones (`src/Sensores.cpp:54`) | noche pérdida a determinada velocidad es una hipótesis a medir, no causa confirmada de los errores |
| Medio | noche contadores signed long sin política de desbordamiento (`src/Sensores.h:44`) | noche límite pendiente para funcionamiento prolongado |
| Medio | noche corrección lineal8, límite25, desvío20 grados/5 cm y desaceleración65 grados están en main (`src/main.cpp:220`, `src/main.cpp:228`, `src/main.cpp:251`) | noche umbrales sin ajuste físico documentado |
| Medio | noche el valor de tolerancia angular2 grados y los20 cm dependen de inercia, resolución y superficie | noche precisión física NO CONFIRMADA |
| Medio | noche Serial usa TxTimeout0 (`src/main.cpp:275`) | noche integridad del registro bajo saturación NO CONFIRMADA |
| Medio | noche el pulso de banco no tiene comprobación de atraso equivalente a la del recorrido (`src/main.cpp:187`, `src/main.cpp:199`) | noche duración física máxima bajo bloqueo NO CONFIRMADA |
| Medio | noche el código no exige enlace USB activo para completar el pulso | noche conducta al desconectar el receptor debe definirse para el modo autónomo |
| Medio | noche plataforma local por symlink (`platformio.ini:8`) y dependencias con rango (`platformio.ini:19`) | noche reproducción en otra PC requiere inventario y disponibilidad de versiones |
| Bajo | noche comentarios y menú aún hablan de cuchilla desconectada (`src/main.cpp:70`, `src/Config.h:7`) | noche desactualizado frente al prototipo sin cuchilla; registrado para corrección de textos |
| Bajo | noche propiedades generadas tienen rutas inexistentes y existe otra configuración MinGW dentro de src | noche problema del editor separado de una falla de movimiento; resolución visual pendiente |

## noche información que falta y decisiones que se agregaron

- noche faltan dimensiones, características de las barreras y duración de la demostración autónoma ya definida.
- noche falta confirmar qué responde ahora `h`, qué responde `b`, si cambia el RGB y si hay reinicios.
- noche falta el esquema de alimentación real con y sin USB, incluidas tensiones medidas durante el pulso.
- noche falta cerrar cuentas por vuelta, errores en reposo y repetibilidad por rueda.
- noche falta una prueba MPU guardada del firmware actual y orientación física del módulo.
- noche falta confirmar modelo/protocolo del sensor de distancia si la autonomía exige evasión.
- noche falta saber si BLE, microSD o cámara son requisitos de la entrega o trabajo posterior.
- noche falta fijar tolerancias físicas de distancia/ángulo, espacio de ensayo y tiempo diario disponible.
- noche se agregaron aquí ocho metas, fechas objetivo, criterios de cierre, crítica del boceto y protocolo de evidencia.
- noche no se implementaron BLE, autonomía nueva, cambios de GPIO ni correcciones eléctricas durante esta revisión documental.
