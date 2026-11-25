# Reconocimiento por barrido doble

Abrí `index.html` en el navegador para recorrer un recinto simulado. La demo arranca en el origen local y descubre el mapa con un sensor frontal ideal y cuatro orientaciones sucesivas del chasis. La cuadrícula usa celdas de 0,25 m. El controlador recibe las lecturas, la pose estimada y la cuadrícula observada.

El primer barrido da prioridad al eje vertical y alterna franjas. Cuando se agotan las celdas libres pendientes alcanzables en esa fase, el segundo cambia la prioridad al eje perpendicular. En cada fase el robot puede volver por terreno observado para retomar celdas pendientes. El mapa distingue celdas desconocidas, libres observadas, ocupadas y visitadas. Una lectura inválida detiene la decisión de movimiento.

## Prueba en computadora

Desde la raíz del repositorio, con Node.js 18 o superior:

```sh
node simulacion/reconocimiento/prueba.cjs
```

La prueba compara el primer rumbo en dos escenarios con idénticas entradas observadas, verifica la parada con una lectura inválida y ejecuta los dos barridos. El recinto real simulado y sus vetos pertenecen al motor físico y a la evaluación. La salida informa los conteos de celdas y movimientos.

## Alcance de esta versión

La pose estimada coincide con la real en esta versión ideal. El entorno está cercado y el movimiento es discreto, con la huella de una celda. La cobertura medida corresponde al interior alcanzable del escenario de prueba. Las esquinas, la huella real, el deslizamiento y el límite abierto entre césped y pavimento requieren escenarios y datos adicionales. La exploración precede a la optimización de recorridos, que queda para una siguiente etapa.

| Escenario | Celdas observadas y visitadas / alcanzables | Celdas nuevas en el segundo eje | Distancia total | Vetos |
| --- | ---: | ---: | ---: | ---: |
| Recinto base | 296 / 296 | 0 | 166,50 m | 0 |
| Recinto con obstáculo adicional | 295 / 295 | 0 | 165,50 m | 0 |

El evaluador calcula el denominador por separado al final, consultando el recinto simulado. El controlador decide sin ese resultado. La distancia incluye las dos pasadas y los traslados entre franjas.
