"use strict";
const assert = require("node:assert/strict");
const { avanzar, crearSimulacion, decidir, evaluarCobertura, pendiente } = require("./reconocimiento.js");

function primerBarrido(sim) {
  for (let i = 0; i < 5; i++) avanzar(sim);
}

const base = crearSimulacion();
const oculto = crearSimulacion({ obstaculoOculto: true });
assert.equal(base.mundo.bloqueada(1, 1), false);
assert.equal(oculto.mundo.bloqueada(1, 1), true);
primerBarrido(base);
primerBarrido(oculto);
assert.deepEqual(base.lecturas, oculto.lecturas);
assert.deepEqual(base.mapa, oculto.mapa);
assert.deepEqual(base.pose, oculto.pose);
assert.deepEqual(base.decisiones[0], oculto.decisiones[0]);
assert.equal(base.decisiones[0].rumbo, 0);
assert.equal(base.mapa.has("1,1"), false);
console.log("OK: obstáculo oculto, entradas idénticas y mismo rumbo inicial.");

const { pose, mapa, visitadas, eje, sentido } = base;
const lecturas = base.lecturas.map(lectura => ({ ...lectura }));
lecturas[0].valida = false;
assert.equal(decidir({ pose, mapa, visitadas, eje, sentido, lecturas }).tipo, "parar");
console.log("OK: el controlador no avanza con una lectura inválida.");

for (const sim of [base, oculto]) {
  for (let i = 0; i < 12000 && ["barrer", "decidir", "mover"].includes(sim.fase); i++) avanzar(sim);
  assert.equal(sim.fase, "pausa");
  assert.equal(sim.vetos, 0);
  assert.ok(sim.pasos > 50);
  assert.ok(sim.decisiones.some(orden => orden.eje === "horizontal"));
  assert.ok(sim.decisiones.some(orden => orden.tipo === "cambio_eje"));
  assert.ok(sim.visitadasVertical.size > 50);
  assert.ok(sim.faseVisitadas.size > 50);
  assert.ok(sim.visitadas.size < sim.mapa.size);
  assert.equal(pendiente(sim), 0);
  const cobertura = evaluarCobertura(sim);
  assert.equal(cobertura.observadasPorcentaje, 100);
  assert.equal(cobertura.visitadasPorcentaje, 100);
  assert.equal(cobertura.alcanzables, sim === base ? 296 : 295);
  assert.equal(cobertura.nuevasEnHorizontal, 0);
  const libres = [...sim.mapa.values()].filter(estado => estado === "libre").length;
  console.log(JSON.stringify({ estado: sim.fase, pasos: sim.pasos, vertical: sim.visitadasVertical.size, horizontal: sim.faseVisitadas.size, libres, pendientes: pendiente(sim), vetos: sim.vetos, cobertura }));
}
