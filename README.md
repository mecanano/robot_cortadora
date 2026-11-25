> noche tarea vigente: diagnóstico independiente de encoders, MPU6050 y único HC-SR04 frontal antes de modificar navegación, según [DIAGNOSTICO_HARDWARE.md](DIAGNOSTICO_HARDWARE.md).
> noche cargar explícitamente con `pio run -e diagnostico -t upload`; el menú nuevo se identifica como DIAG-S3-20261115-v1 y no activa navegación.
> noche el entorno original se conserva; sus instrucciones históricas de abajo no corresponden al diagnóstico nuevo.
> noche estado en [AVANCES.md](AVANCES.md), plan en [PLAN_HASTA_16_NOVIEMBRE.md](PLAN_HASTA_16_NOVIEMBRE.md), reglas en [RULES.md](RULES.md); la autonomía aún no está aprobada.

# Robot cortacesped - prueba de encoders y MPU

Waveshare ESP32-S3-ETH. Prueba solicitada: avanzar 20 cm, detenerse 500 ms, girar 90 grados a la derecha sobre el lugar y detenerse. Se ejecuta una sola vez al enviar `a`. Arranca detenido. `src/main.cpp` llama a las clases reales de sensores y motores; no hay programa de prueba separado.

El ultrasonico queda fuera: `robot.sensor.init(false, false)` no configura sus GPIO y no se llama a su actualizacion. No se borro su clase para poder retomarla mas adelante. Tampoco se usan camara, microSD, Ethernet, HC-05 ni cuchilla.

## Conexion actual

| Componente | GPIO |
|---|---|
| Encoder izquierdo A/B | 38/39 |
| Encoder derecho A/B | 43/44 |
| MPU6050 SDA/SCL | 16/17 |
| RGB integrado | 21 |
| L298N derecho ENA/IN1/IN2 | 40/41/42 |
| L298N izquierdo ENB/IN3/IN4 | 47/48/15 |
| BOOT (parada por software) | 0 |

Mantener camara desconectada: el mapa usa varias de sus senales. IO21 solo RGB; IN4 izquierdo en IO15. USB nativo 19/20 reservado al monitor. No usar GPIO33..37. Sensor y encoders con niveles de 3.3 V. GND comun entre placa, sensores y driver. Motor alimentado por su driver/fuente adecuada. Retirar jumpers ENA/ENB del L298N. Cuchilla desconectada.

La rutina requiere MPU6050 con Z vertical hacia arriba, robot horizontal al calibrar. Direccion I2C por defecto 0x68 (AD0 a GND); cambiar MPU_DIRECCION a 0x69 si AD0 esta a 3.3 V. El lector comprueba transacciones I2C, longitud de datos, identidad y rangos. Un fallo posterior invalida los valores y requiere reiniciar/calibrar; no se siguen mostrando valores antiguos como validos.

## Prueba individual de motores

noche enviar `t` ejecuta una sola secuencia: derecho adelante 3000 ms (azul), pausa 500 ms (verde), izquierdo adelante 3000 ms (magenta) y parada (verde).
noche se imprimen los pines configurados para revisar el cableado y las cuentas/errores al terminar cada motor; s, espacio o BOOT cancelan también durante la pausa.

Con ruedas levantadas, camara y cuchilla desconectadas, cargar firmware y abrir COM3 a 115200. Enviar un comando por vez: `d` derecho adelante, `f` derecho atras, `i` izquierdo adelante, `j` izquierdo atras, `b` ambos adelante. Cada comando llama a `robot.motor.setMotores()` desde main.cpp durante 3000 ms a PWM 120 y luego detiene. No necesita MPU ni cuentas por vuelta. `s`, espacio o BOOT detienen antes del plazo. Esperar al menos 500 ms entre movimientos; una nueva orden de movimiento durante una prueba la cancela y exige reenviarla despues de la pausa.

RGB derecho azul, izquierdo magenta, ambos blanco; vuelve a verde al terminar. Durante el pulso y al finalizar muestra cuentas y errores de ambos encoders. Es un diagnostico: no detiene por errores de encoder y no calcula cuentas por vuelta. Registrar que rueda gira, sentido real y salida de consola. El sentido fisico debe verificarse antes del recorrido. El ultrasonico permanece desactivado.

## Primero: medir las cuentas por vuelta

Diametro de rueda informado: **6 cm**; circunferencia geometrica aproximada 18.85 cm. Para avanzar 20 cm se necesitan aproximadamente 1.06 vueltas, pero faltan las cuentas por vuelta de tus encoders. El codigo NO inventa esos datos: CUENTAS_VUELTA_IZQ/DER estan en cero y se rechaza el recorrido con a hasta calibrar; los pulsos de banco siguen disponibles.

1. Cargar firmware por COM3 y abrir monitor a 115200. `h` vuelve a imprimir ayuda si se perdio el mensaje de inicio.
2. Con el robot detenido y las ruedas levantadas, marcar cada rueda y enviar `r`: pone cuentas/errores en cero y comienza la captura.
3. Girar la rueda izquierda **una vuelta completa hacia ADELANTE**. Girar la derecha tambien **una vuelta completa hacia ADELANTE**. Hacerlo por separado para verificar que cuenta el lado correcto. No son vueltas del eje del motor.
4. Enviar `k`. Se rechaza si falta alguna vuelta/cuenta, hay menos de cuatro cuentas por lado o hay errores de transicion.
5. La consola muestra cuentas por vuelta y signo de cada encoder. Quedan en RAM hasta reiniciar. Copiarlas a CUENTAS_VUELTA_IZQ/DER y SIGNO_ENCODER_IZQ/DER de Config.h si se quieren conservar. Repetir para comprobar consistencia. El firmware solo verifica cuentas/errores: no puede certificar que fisicamente se haya girado exactamente una vuelta.

Con pocas cuentas por vuelta la distancia tiene pasos grandes; la consola muestra centimetros por cuenta. No se promete exactitud de 20 cm sin comprobar el diametro efectivo y el deslizamiento sobre el suelo.

## Segundo: comprobar y calibrar MPU

6. Apoyar el robot horizontal y quieto, enviar `c`. Los motores permanecen detenidos. Se toman 500 muestras; demora al menos 1 s mas I2C. Se rechaza un fallo I2C o giro excesivo detectado durante la calibracion. Esta comprobacion no detecta todos los posibles movimientos/vibraciones.
7. Enviar `g` y girar el robot **a mano hacia la derecha**, sin inclinarlo. `grados_derecha` debe aumentar. El valor se calcula integrando gz; el MPU6050 no proporciona rumbo absoluto.
8. Si aumenta en negativo, revisar orientacion Z o cambiar SIGNO_GIRO_DERECHA entre -1 y +1 antes de probar movimiento. El valor por defecto es -1 para Z hacia arriba. `p` permite detectar y leer MPU sin calibrar, pero no habilita el recorrido.

Si persisten errores I2C del MPU, NO se habilita la secuencia de movimiento. Revisar el montaje antes de continuar.

## Tercero: recorrido por comando

9. Bajar el robot al suelo y colocarlo en una zona despejada, con el driver de motores alimentado y la cuchilla desconectada. Confirmar el cambio de IN4 a IO15 y que ambos motores giran hacia adelante para orden PWM positiva. Los signos medidos de encoder no corrigen un motor cableado al reves.
10. Enviar `a`: avance por cuentas, pausa, giro derecho estimado de 90 grados por giroscopio y parada. El giro usa derecho atras e izquierdo adelante. El control desacelera durante la parte final del giro y solicita parada con tolerancia de 2 grados; inercia y deslizamiento pueden cambiar el resultado fisico.
11. Comparar con marcas en el piso y una regla/escuadra. La secuencia no se repite automaticamente. Al reiniciar hay que calibrar MPU de nuevo y repetir r/k si no se guardaron las cuentas en Config.h.

## Comandos y colores

| Comando/etapa | Accion | RGB |
|---|---|---|
| h | Parar y ayuda | Verde |
| e | Leer cuentas y errores | Cian |
| d / f | Derecho adelante / atras, pulso de 3000 ms | Azul |
| i / j | Izquierdo adelante / atras, pulso de 3000 ms | Magenta |
| b | Ambos adelante, pulso de 3000 ms | Blanco |
| r | Parar, cero y comenzar captura de una vuelta por rueda | Cian |
| k | Validar/guardar cuentas y signos en RAM | Verde o rojo si falla |
| p | Detectar/leer MPU | Amarillo o rojo si falla |
| c | Calibrar MPU quieto | Amarillo |
| g | Giro manual para verificar signo de gz | Amarillo |
| a: avance | Avance objetivo 20 cm con correccion de diferencia entre ruedas | Azul |
| a: pausa | Solicitar PWM cero durante 500 ms | Verde |
| a: giro | Giro derecho objetivo 90 grados | Magenta |
| s o espacio | Parar/cancelar | Verde |
| Error | Solicitar parada; no reanudar automaticamente | Rojo |

`u` ya no se usa y `m` tampoco inicia la antigua secuencia temporizada. Toda orden reconocida detiene la maniobra antes de cambiar de accion. BOOT presionado durante banco/avance/pausa/giro solicita parada. Es una parada por software, no reemplaza un corte fisico de alimentacion.

## Limites de la prueba

Control nominal cada 20 ms. La rutina solicita parada por falta de progreso de ruedas/giro durante 1.5 s, error de cuadratura, MPU/I2C invalido, muestras/control demasiado atrasados, rueda en sentido contrario, desvio excesivo, timeout de avance de 10 s o giro de 8 s. Un robot puede desplazarse antes de detectar una falla; estas comprobaciones no equivalen a una garantia de seguridad fisica.

Cada rueda se detiene al alcanzar su cuenta objetivo. Hay correccion proporcional simple entre distancias de ruedas, no un PID de velocidad completo. El giro se integra desde la pausa; el avance se estima con ruedas y no detecta patinamiento. No hay deteccion de obstaculos al estar el ultrasonico desactivado.

Los colores identifican etapa/estado, no certifican medidas reales. La compilacion y las simulaciones de control no sustituyen pruebas fisicas. La configuracion PlatformIO de camara/memoria y el mapa definitivo para todos los perifericos siguen pendientes. La plataforma symlink requiere adaptar su ruta en otra PC.
