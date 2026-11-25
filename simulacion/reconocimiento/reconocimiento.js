"use strict";

const reconocimiento = (() => {
  // Cada celda representa 0,25 m. El eje +Y es el rumbo inicial.
  const DIRECCIONES = [
    { dx: 0, dy: 1, nombre: "Norte" },
    { dx: 1, dy: 0, nombre: "Este" },
    { dx: 0, dy: -1, nombre: "Sur" },
    { dx: -1, dy: 0, nombre: "Oeste" },
  ];
  const PASO_M = 0.25;
  const ALCANCE = 5;
  const VENTANA = 30;
  const key = (x, y) => x + "," + y;
  const mover = ({ x, y }, rumbo, pasos = 1) => ({
    x: x + DIRECCIONES[rumbo].dx * pasos,
    y: y + DIRECCIONES[rumbo].dy * pasos,
  });

  function crearMundo({ obstaculoOculto = false } = {}) {
    const ocupadas = new Set();
    const rect = (x0, y0, x1, y1) => {
      for (let x = x0; x <= x1; x++) {
        for (let y = y0; y <= y1; y++) ocupadas.add(key(x, y));
      }
    };
    rect(4, 4, 6, 8);
    rect(10, 0, 12, 2);
    rect(12, 9, 15, 10);
    rect(16, -2, 19, 3);
    if (obstaculoOculto) rect(1, 1, 1, 1);
    return {
      bloqueada(x, y) {
        return x < -2 || x > 19 || y < -2 || y > 13 || ocupadas.has(key(x, y));
      },
      medir({ x, y, rumbo }) {
        for (let pasos = 1; pasos <= ALCANCE; pasos++) {
          const punto = mover({ x, y }, rumbo, pasos);
          if (this.bloqueada(punto.x, punto.y)) return { rumbo, pasos, eco: true, valida: true };
        }
        return { rumbo, pasos: ALCANCE, eco: false, valida: true };
      },
    };
  }

  function actualizarMapa(mapa, pose, lectura) {
    if (!lectura.valida) return;
    for (let pasos = 1; pasos <= lectura.pasos; pasos++) {
      const { x, y } = mover(pose, lectura.rumbo, pasos);
      if (Math.abs(x) > VENTANA || Math.abs(y) > VENTANA) continue;
      const id = key(x, y);
      const ocupada = pasos === lectura.pasos && lectura.eco;
      if (ocupada || mapa.get(id) !== "ocupada") mapa.set(id, ocupada ? "ocupada" : "libre");
    }
  }

  // La ruta de regreso por celdas libres busca la candidata observada más cercana.
  function rutaAPendiente(pose, mapa, visitadas, orden) {
    const cola = [{ x: pose.x, y: pose.y, primero: null }];
    const vistos = new Set([key(pose.x, pose.y)]);
    for (let i = 0; i < cola.length; i++) {
      const actual = cola[i];
      for (const rumbo of orden) {
        const vecino = mover(actual, rumbo);
        const id = key(vecino.x, vecino.y);
        if (vistos.has(id) || mapa.get(id) !== "libre") continue;
        const primero = actual.primero ?? rumbo;
        if (!visitadas.has(id)) return primero;
        vistos.add(id);
        cola.push({ ...vecino, primero });
      }
    }
    return null;
  }

  function decidir({ pose, lecturas, mapa, visitadas, eje, sentido }) {
    if (lecturas.length !== 4 || lecturas.some(lectura => !lectura.valida)) {
      return { tipo: "parar", motivo: "Barrido incompleto o lectura inválida" };
    }
    const lateral = eje === "vertical" ? 1 : 0;
    const opuesto = (sentido + 2) % 4;
    const otroLado = (lateral + 2) % 4;
    const orden = [sentido, lateral, opuesto, otroLado];
    const objetivo = orden.find(rumbo => {
      const { x, y } = mover(pose, rumbo);
      const id = key(x, y);
      return mapa.get(id) === "libre" && !visitadas.has(id);
    });
    if (objetivo === sentido) return { tipo: "mover", rumbo: sentido, eje, sentido, motivo: "Seguir franja" };
    if (objetivo === lateral || objetivo === otroLado) {
      return { tipo: "mover", rumbo: objetivo, eje, sentido: opuesto, motivo: "Cambiar franja y alternar sentido" };
    }
    if (objetivo === opuesto) return { tipo: "mover", rumbo: opuesto, eje, sentido: opuesto, motivo: "Explorar el sentido opuesto" };

    const rumbo = rutaAPendiente(pose, mapa, visitadas, orden);
    if (rumbo === null) return { tipo: "pausa", motivo: "Sin celdas libres pendientes alcanzables con el mapa observado" };
    return { tipo: "mover", rumbo, eje, sentido, motivo: "Retomar una franja pendiente por suelo observado" };
  }

  function crearSimulacion(opciones = {}) {
    const mundo = crearMundo(opciones);
    const inicial = { x: 0, y: 0, rumbo: 0 };
    const sim = {
      pose: { ...inicial }, real: { ...inicial }, inicial,
      mapa: new Map([[key(0, 0), "libre"]]),
      visitadas: new Set([key(0, 0)]),
      traza: [{ ...inicial }],
      lecturas: [], decisiones: [], vetos: 0, fase: "barrer",
      eje: "vertical", sentido: 0, pasos: 0, mundo,
      faseVisitadas: new Set([key(0, 0)]), visitadasVertical: null, libresAlCambiarEje: null,
    };
    return sim;
  }

  function avanzar(sim) {
    if (sim.fase === "barrer") {
      const rumbo = sim.lecturas.length;
      sim.pose.rumbo = rumbo;
      sim.real.rumbo = rumbo;
      const lectura = sim.mundo.medir(sim.real);
      sim.lecturas.push(lectura);
      actualizarMapa(sim.mapa, sim.pose, lectura);
      if (sim.lecturas.length === 4) sim.fase = "decidir";
    } else if (sim.fase === "decidir") {
      const { pose, lecturas, mapa, faseVisitadas, eje, sentido } = sim;
      const orden = decidir({ pose, lecturas, mapa, visitadas: faseVisitadas, eje, sentido });
      if (orden.tipo === "pausa" && eje === "vertical") {
        sim.decisiones.push({ tipo: "cambio_eje", motivo: "Visitar las franjas del eje perpendicular" });
        sim.visitadasVertical = faseVisitadas;
        sim.libresAlCambiarEje = new Set([...mapa].filter(([, estado]) => estado === "libre").map(([id]) => id));
        sim.faseVisitadas = new Set([key(pose.x, pose.y)]);
        sim.eje = "horizontal";
        sim.sentido = 1;
        return;
      }
      sim.decisiones.push(orden);
      sim.fase = orden.tipo;
    } else if (sim.fase === "mover") {
      const orden = sim.decisiones.at(-1);
      const siguiente = mover(sim.real, orden.rumbo);
      const estimada = mover(sim.pose, orden.rumbo);

      // El motor de simulación veta desplazamientos. El controlador nunca recibe el escenario.
      if (sim.mundo.bloqueada(siguiente.x, siguiente.y)) {
        sim.vetos++;
        sim.fase = "veto";
        return;
      }
      sim.real = { ...siguiente, rumbo: orden.rumbo };
      sim.pose = { ...estimada, rumbo: orden.rumbo };
      const id = key(sim.pose.x, sim.pose.y);
      sim.visitadas.add(id);
      sim.faseVisitadas.add(id);
      sim.traza.push({ ...sim.pose, eje: sim.eje });
      sim.pasos++;
      sim.eje = orden.eje;
      sim.sentido = orden.sentido;
      sim.lecturas = [];
      sim.fase = "barrer";
    }
  }

  function pendiente(sim, visitadas = sim.faseVisitadas) {
    return [...sim.mapa].filter(([id, estado]) => estado === "libre" && !visitadas.has(id)).length;
  }

  // Evaluación posterior con el recinto real del simulador, fuera del controlador.
  function evaluarCobertura(sim) {
    const cola = [sim.inicial];
    const alcanzables = new Set([key(sim.inicial.x, sim.inicial.y)]);
    for (let i = 0; i < cola.length; i++) {
      for (let rumbo = 0; rumbo < DIRECCIONES.length; rumbo++) {
        const vecino = mover(cola[i], rumbo);
        const id = key(vecino.x, vecino.y);
        if (alcanzables.has(id) || sim.mundo.bloqueada(vecino.x, vecino.y)) continue;
        alcanzables.add(id);
        cola.push(vecino);
      }
    }
    let observadas = 0;
    let visitadas = 0;
    let nuevasEnHorizontal = 0;
    for (const id of alcanzables) {
      if (sim.mapa.get(id) === "libre") {
        observadas++;
        if (sim.libresAlCambiarEje && !sim.libresAlCambiarEje.has(id)) nuevasEnHorizontal++;
      }
      if (sim.visitadas.has(id)) visitadas++;
    }
    return {
      alcanzables: alcanzables.size,
      observadas,
      visitadas,
      observadasPorcentaje: 100 * observadas / alcanzables.size,
      visitadasPorcentaje: 100 * visitadas / alcanzables.size,
      nuevasEnHorizontal,
      areaNuevaHorizontalM2: nuevasEnHorizontal * PASO_M ** 2,
    };
  }

  return { avanzar, crearSimulacion, decidir, evaluarCobertura, pendiente, PASO_M, DIRECCIONES };
})();

if (typeof module !== "undefined") module.exports = reconocimiento;
