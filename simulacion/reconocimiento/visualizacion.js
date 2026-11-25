"use strict";
const tablero = document.querySelector("canvas");
const ctx = tablero.getContext("2d");
const { avanzar, crearSimulacion, evaluarCobertura, pendiente, PASO_M, DIRECCIONES } = reconocimiento;
const elementos = Object.fromEntries(
  ["reproducir", "paso", "finalizar", "reiniciar", "oculto", "referencia", "fase", "decision", "libres", "pendientes", "visitadas", "distancia", "vetos", "cobertura"]
    .map(id => [id, document.getElementById(id)])
);
const unidad = 26;
const izquierda = -4;
const arriba = 15;
const activas = new Set(["barrer", "decidir", "mover"]);
const estados = { barrer: "Giro y lectura frontal", decidir: "Selección de rumbo", mover: "Desplazamiento", pausa: "Pausa: mapa observado recorrido", parar: "Parada por lectura", veto: "Parada por veto virtual" };
let sim = crearSimulacion();
let temporizador = null;

function caja(x, y) {
  return [(x - izquierda) * unidad, (arriba - y) * unidad];
}

function centro(x, y) {
  return caja(x, y).map(p => p + unidad / 2);
}

function dibujar() {
  ctx.fillStyle = "#172321";
  ctx.fillRect(0, 0, tablero.width, tablero.height);
  for (let y = arriba; y > arriba - tablero.height / unidad; y--) {
    for (let x = izquierda; x < izquierda + tablero.width / unidad; x++) {
      const [px, py] = caja(x, y);
      const id = x + "," + y;
      const estado = sim.mapa.get(id);
      if (estado) {
        ctx.fillStyle = estado === "ocupada" ? "#bd654e" : sim.faseVisitadas.has(id) ? "#88b996" : "#32664b";
        ctx.fillRect(px, py, unidad, unidad);
      }
      ctx.strokeStyle = "#233531";
      ctx.strokeRect(px, py, unidad, unidad);
      if (elementos.referencia.checked && sim.mundo.bloqueada(x, y)) {
        ctx.strokeStyle = "#bca59a";
        ctx.strokeRect(px + 3, py + 3, unidad - 6, unidad - 6);
      }
    }
  }
  ctx.lineWidth = 1.5;
  for (let i = 1; i < sim.traza.length; i++) {
    const anterior = sim.traza[i - 1];
    const actual = sim.traza[i];
    ctx.beginPath();
    ctx.moveTo(...centro(anterior.x, anterior.y));
    ctx.lineTo(...centro(actual.x, actual.y));
    ctx.strokeStyle = actual.eje === "horizontal" ? "#99d7ed" : "#f9d980";
    ctx.stroke();
  }
  const [origenX, origenY] = centro(0, 0);
  ctx.lineWidth = 1;
  ctx.strokeStyle = "#f5e5a7";
  ctx.strokeRect(origenX - 4, origenY - 4, 8, 8);
  const robot = sim.pose;
  const rumbo = DIRECCIONES[robot.rumbo];
  const [robotX, robotY] = centro(robot.x, robot.y);
  ctx.fillStyle = "#f8fcf7";
  ctx.beginPath();
  ctx.arc(robotX, robotY, 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(robotX, robotY);
  ctx.lineTo(robotX + rumbo.dx * 13, robotY - rumbo.dy * 13);
  ctx.strokeStyle = "#f8fcf7";
  ctx.stroke();
  ctx.lineWidth = 1;
}

function mostrar() {
  dibujar();
  const activa = activas.has(sim.fase);
  const estado = estados[sim.fase];
  const vertical = sim.visitadasVertical?.size ?? sim.faseVisitadas.size;
  const horizontal = sim.eje === "horizontal" ? sim.faseVisitadas.size : 0;
  elementos.reproducir.textContent = temporizador === null ? "Iniciar" : "Pausar";
  elementos.reproducir.disabled = elementos.paso.disabled = elementos.finalizar.disabled = !activa;
  elementos.fase.textContent = (sim.eje === "vertical" ? "1 · Vertical" : "2 · Horizontal") + " / " + estado;
  elementos.decision.textContent = sim.decisiones.at(-1)?.motivo ?? "Preparando el primer barrido";
  elementos.libres.textContent = [...sim.mapa.values()].filter(estado => estado === "libre").length;
  elementos.pendientes.textContent = pendiente(sim);
  elementos.visitadas.textContent = vertical + " verticales · " + horizontal + " horizontales";
  elementos.distancia.textContent = (sim.pasos * PASO_M).toLocaleString("es-AR", { maximumFractionDigits: 2 }) + " m";
  elementos.vetos.textContent = sim.vetos;
  if (activa) elementos.cobertura.textContent = "Al finalizar";
  else {
    const { observadasPorcentaje, visitadasPorcentaje, nuevasEnHorizontal } = evaluarCobertura(sim);
    const porcentaje = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 1 });
    elementos.cobertura.textContent = porcentaje.format(observadasPorcentaje) + " % observado · "
      + porcentaje.format(visitadasPorcentaje) + " % visitado · " + nuevasEnHorizontal + " celdas nuevas en el segundo eje";
  }
}

function pausar() {
  if (temporizador !== null) clearInterval(temporizador);
  temporizador = null;
}

function ejecutarPasos(cantidad) {
  for (let i = 0; i < cantidad && activas.has(sim.fase); i++) avanzar(sim);
  if (!activas.has(sim.fase)) pausar();
  mostrar();
}

function reiniciar() {
  pausar();
  sim = crearSimulacion({ obstaculoOculto: elementos.oculto.checked });
  mostrar();
}

elementos.reproducir.onclick = () => {
  if (temporizador !== null) pausar();
  else temporizador = setInterval(() => ejecutarPasos(12), 50);
  mostrar();
};
elementos.paso.onclick = () => {
  pausar();
  ejecutarPasos(sim.fase === "barrer" ? 4 - sim.lecturas.length : 1);
};
elementos.finalizar.onclick = () => {
  pausar();
  ejecutarPasos(12000);
};
elementos.reiniciar.onclick = reiniciar;
elementos.oculto.onchange = reiniciar;
elementos.referencia.onchange = mostrar;
mostrar();
