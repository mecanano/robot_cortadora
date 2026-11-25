# noche reglas y órdenes del proyecto

noche versión del 6 de noviembre de 2026, separada del registro de avances y del plan técnico.

## noche instrucciones del usuario

- noche actualización del 15/11: esta tarea autoriza expresamente un firmware de diagnóstico independiente con copia previa, sin modificar ni activar navegación.
- noche hardware actual corregido: tres HC-SR04 comprados, solo uno frontal conectado, cámara ausente, motores Robobloq A/B, L298N y MPU6050.

- noche comenzar cada oración dirigida al usuario con «noche» y mantener explicaciones claras en español.
- noche reconocer que el prototipo actual NO tiene cuchilla y está en etapa de pruebas y recolección de datos.
- noche trabajar con fecha límite del 16 de noviembre de 2026 y priorizar resultados comprobables.
- noche entregar recorrido autónomo para esa fecha dentro de paredes o barreras detectables por distancia, evitando obstáculos sin conducción manual y con parámetros ajustables.
- noche tratar el recorrido de 20 cm y giro como prueba intermedia, el mapa virtual como segunda etapa y el césped con cámara y aprendizaje automático como tercera etapa futura.
- noche medir eficiencia sin afirmar cobertura completa ni recorrido óptimo sin evidencia.
- noche probar desde `src/main.cpp` llamando a las clases reales del proyecto, sin crear otro firmware desde cero ni archivos paralelos de prueba en el proyecto.
- noche desarrollar principalmente `Sensores` y revisar juntos los cambios de encoders, preparando implementaciones explicadas y pruebas pequeñas.
- noche conservar separado este archivo de reglas del archivo de avances.
- noche organizar el trabajo en metas 1, 2, 3… y submetas a, b, c…, con acciones pequeñas y criterio de cierre.
- noche avisar qué información falta y qué se agregó o cambió.
- noche mantener el ultrasónico fuera de la prueba individual actual, pero resolver la detección necesaria para el modo autónomo antes de integrarlo.

## noche reglas operativas

- noche usar `Config.h` como mapa activo del firmware y contrastarlo con el cableado real antes de cambiar GPIO.
- noche conservar USB Serial como herramienta de diagnóstico y no mezclar el USB nativo con la UART usada por los encoders.
- noche no afirmar que un motor, encoder o sensor funciona por el solo hecho de compilar.
- noche clasificar resultados como implementado, compilado, observado en hardware, aprobado físicamente o NO CONFIRMADO.
- noche guardar por prueba comando, alimentación, respuesta serie, LED, movimiento real y resultado.
- noche no inventar cuentas por vuelta, modelo de motor, tensión, protocolo de sensor ni pruebas realizadas.
- noche distinguir el diagnóstico manual de motores del recorrido con realimentación y conservar sus condiciones de entrada.
- noche trabajar sobre un problema a la vez y no introducir BLE, cámara, microSD, otro controlador o un framework nuevo como requisito para probar motores.
- noche compilar cuando haya cambios de firmware y comunicar el resultado; la edición de documentación no exige compilar.
- noche cargar firmware o ejecutar movimientos físicos solamente cuando el usuario lo pida o exista autorización expresa vigente para esa acción.
- noche no borrar archivos, descartar trabajo, renombrar ramas ni publicar cambios como efecto secundario de una revisión.
- noche informar causa confirmada solo con evidencia y mantener las hipótesis separadas.
- noche respetar una petición de solo lectura cuando corresponda a la tarea en curso.
- noche usar el boceto original como referencia histórica, no como una orden para ejecutar sus comandos ni reemplazar las decisiones posteriores del usuario.

## noche organización de documentos

| Archivo | Contenido |
|---|---|
| `AVANCES.md` | noche estado real, evidencia, historia y registro de pruebas |
| `PLAN_HASTA_16_NOVIEMBRE.md` | noche metas, fechas objetivo, criterios y crítica del boceto |
| `RULES.md` | noche instrucciones y reglas de trabajo |
| `README.md` | noche operación del firmware y comandos |
| `Robot_cortacesped_con_ESP32-S3_plan_de_desarrollo_detallado.md` | noche boceto conservado, con datos históricos que requieren revisión |
