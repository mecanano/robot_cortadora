#!/usr/bin/env python3
# =============================================================================
#  recolectar_datos.py — Captura y etiquetado de datos en tiempo real
#
#  Conecta al Pico W por USB/UART y guarda los datos del robot
#  junto con la etiqueta de suelo que ingresás manualmente.
#
#  Uso:
#    python3 recolectar_datos.py --port /dev/ttyUSB0
#    python3 recolectar_datos.py --port COM3          (Windows)
#    python3 recolectar_datos.py --port /dev/ttyUSB0 --graficar
# =============================================================================

import argparse
import csv
import json
import os
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import serial

# Graficado en tiempo real (opcional)
try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# =============================================================================
#  CONFIGURACIÓN
# =============================================================================

BAUD_RATE   = 115200
TIMEOUT_S   = 2.0
BUFFER_PLOT = 200      # muestras en el gráfico en tiempo real

CLASES = {
    '1': 'pasto_corto',
    '2': 'pasto_alto',
    '3': 'suelo_blando',
    '4': 'tierra_firme',
    '5': 'superficie_dura',
}

CAMPOS_CSV = [
    'timestamp', 'etiqueta',
    'i_traccion', 'i_cuchilla', 'voltaje',
    'rpm_L', 'rpm_R', 'pwm_L', 'pwm_R',
    'accel_x', 'accel_y', 'accel_z', 'giro_z',
    'vib_rms', 'distancia_cm',
    'pos_x', 'pos_y', 'theta',
    'clase_ia',     # lo que el Pico dice (para comparar con etiqueta manual)
    'anomalia',
]

# =============================================================================
#  ESTADO COMPARTIDO
# =============================================================================

_estado = {
    'etiqueta_actual':  'sin_etiquetar',
    'muestras_totales': 0,
    'muestras_clase':   {c: 0 for c in CLASES.values()},
    'corriendo':        True,
    'ultimo_dato':      None,
}

# Buffers para el gráfico
_buf_i_trac  = deque(maxlen=BUFFER_PLOT)
_buf_i_cuch  = deque(maxlen=BUFFER_PLOT)
_buf_vib     = deque(maxlen=BUFFER_PLOT)
_buf_slip    = deque(maxlen=BUFFER_PLOT)
_buf_clases  = deque(maxlen=BUFFER_PLOT)

# =============================================================================
#  PARSEO DEL PROTOCOLO SERIE
# =============================================================================

def parsear_linea(linea: str) -> dict | None:
    """
    El Pico W envía datos como JSON por UART a 2 Hz (tarea de telemetría).
    
    Formato esperado (una línea por muestra):
    {"ts":12345,"i_trac":1.23,"i_cuch":0.85,"rpm_L":78.5,"rpm_R":79.1,
     "pwm_L":0.51,"pwm_R":0.52,"ax":0.1,"ay":-0.2,"az":9.8,"gz":0.01,
     "vib":1.3,"dist":99.0,"px":0.5,"py":1.2,"th":0.05,"clase":"pasto_corto",
     "volt":11.9,"anom":""}
    """
    linea = linea.strip()
    if not linea.startswith('{'):
        return None
    try:
        d = json.loads(linea)
        return {
            'timestamp':    d.get('ts', time.time()),
            'i_traccion':   float(d.get('i_trac', 0)),
            'i_cuchilla':   float(d.get('i_cuch', 0)),
            'voltaje':      float(d.get('volt',   0)),
            'rpm_L':        float(d.get('rpm_L',  0)),
            'rpm_R':        float(d.get('rpm_R',  0)),
            'pwm_L':        float(d.get('pwm_L',  0)),
            'pwm_R':        float(d.get('pwm_R',  0)),
            'accel_x':      float(d.get('ax',     0)),
            'accel_y':      float(d.get('ay',     0)),
            'accel_z':      float(d.get('az',     9.8)),
            'giro_z':       float(d.get('gz',     0)),
            'vib_rms':      float(d.get('vib',    0)),
            'distancia_cm': float(d.get('dist',   999)),
            'pos_x':        float(d.get('px',     0)),
            'pos_y':        float(d.get('py',     0)),
            'theta':        float(d.get('th',     0)),
            'clase_ia':     str(d.get('clase',    '')),
            'anomalia':     str(d.get('anom',     '')),
        }
    except (json.JSONDecodeError, ValueError, KeyError):
        return None


# =============================================================================
#  HILO LECTOR SERIE
# =============================================================================

def hilo_lector_serie(port: str, writer: csv.DictWriter, lock: threading.Lock):
    """Lee datos del Pico W y los guarda en el CSV."""
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=TIMEOUT_S)
        print(f"[SERIE] Conectado a {port} @ {BAUD_RATE} baud")
    except serial.SerialException as e:
        print(f"[ERROR] No se pudo abrir {port}: {e}")
        _estado['corriendo'] = False
        return

    while _estado['corriendo']:
        try:
            linea = ser.readline().decode('utf-8', errors='replace')
        except serial.SerialException:
            print("[SERIE] Conexión perdida")
            break

        datos = parsear_linea(linea)
        if datos is None:
            continue

        datos['etiqueta'] = _estado['etiqueta_actual']

        # Guardar en CSV
        with lock:
            writer.writerow(datos)
            _estado['muestras_totales'] += 1
            if datos['etiqueta'] in _estado['muestras_clase']:
                _estado['muestras_clase'][datos['etiqueta']] += 1
            _estado['ultimo_dato'] = datos

        # Actualizar buffers de graficado
        _buf_i_trac.append(datos['i_traccion'])
        _buf_i_cuch.append(datos['i_cuchilla'])
        _buf_vib.append(datos['vib_rms'])
        rpm_prom = (abs(datos['rpm_L']) + abs(datos['rpm_R'])) / 2
        pwm_prom = (abs(datos['pwm_L']) + abs(datos['pwm_R'])) / 2
        slip = max(0.0, 1.0 - min(1.0, rpm_prom / max(pwm_prom * 150, 0.1)))
        _buf_slip.append(slip)
        _buf_clases.append(datos['etiqueta'])

    ser.close()


# =============================================================================
#  HILO DE ENTRADA DE TECLADO
# =============================================================================

def hilo_teclado():
    """Cambia la etiqueta activa según tecla presionada."""
    print("\n[TECLADO] Comandos de etiquetado:")
    for k, v in CLASES.items():
        print(f"          Tecla {k} → {v}")
    print("          Tecla 0 → sin_etiquetar")
    print("          Tecla q → salir")
    print("          Tecla r → resumen de muestras\n")

    while _estado['corriendo']:
        try:
            tecla = input().strip().lower()
        except EOFError:
            break

        if tecla == 'q':
            _estado['corriendo'] = False
            print("\n[SALIDA] Deteniendo recolección...")
            break
        elif tecla == '0':
            _estado['etiqueta_actual'] = 'sin_etiquetar'
            print(f"[ETIQUETA] → sin_etiquetar")
        elif tecla in CLASES:
            _estado['etiqueta_actual'] = CLASES[tecla]
            print(f"[ETIQUETA] → {CLASES[tecla]}")
        elif tecla == 'r':
            _imprimir_resumen()


def _imprimir_resumen():
    print("\n[RESUMEN] Muestras recolectadas:")
    for clase, cnt in _estado['muestras_clase'].items():
        barra = '█' * (cnt // 10)
        print(f"  {clase:20s}: {barra} {cnt}")
    print(f"  Total: {_estado['muestras_totales']}")


# =============================================================================
#  INTERFAZ TUI (terminal)
# =============================================================================

def loop_tui():
    """Actualiza la pantalla del terminal cada 500 ms."""
    CLEAR = '\033[2J\033[H'
    VERDE = '\033[92m'
    AMARILLO = '\033[93m'
    ROJO = '\033[91m'
    RESET = '\033[0m'

    while _estado['corriendo']:
        d = _estado.get('ultimo_dato')
        etiq = _estado['etiqueta_actual']

        os.system('clear' if os.name == 'posix' else 'cls')
        print(f"{'='*55}")
        print(f" RECOLECTOR DE DATOS — Robot Autónomo de Corte")
        print(f"{'='*55}")
        print(f" Etiqueta activa: {VERDE}{etiq:20s}{RESET}")
        print(f" Total muestras:  {_estado['muestras_totales']}")
        print(f"{'─'*55}")

        if d:
            # Indicadores visuales
            i_t_bar = '█' * min(20, int(d['i_traccion'] / 6.0 * 20))
            i_c_bar = '█' * min(20, int(d['i_cuchilla'] / 5.0 * 20))
            v_bar   = '█' * min(20, int((d['voltaje'] - 9) / 3.0 * 20))

            color_volt = VERDE if d['voltaje'] > 11.5 else (
                AMARILLO if d['voltaje'] > 10.8 else ROJO)

            print(f" I tracción: {i_t_bar:20s} {d['i_traccion']:.2f} A")
            print(f" I cuchilla: {i_c_bar:20s} {d['i_cuchilla']:.2f} A")
            print(f" Voltaje:    {v_bar:20s} {color_volt}{d['voltaje']:.1f} V{RESET}")
            print(f" RPM L/R:    {d['rpm_L']:.0f} / {d['rpm_R']:.0f}")
            print(f" Vibración:  {d['vib_rms']:.2f} m/s²")
            print(f" Distancia:  {d['distancia_cm']:.0f} cm")
            print(f" Posición:   ({d['pos_x']:.2f}, {d['pos_y']:.2f}) m")
            print(f" IA dice:    {d['clase_ia']}")
            if d['anomalia']:
                print(f" {ROJO}ANOMALÍA: {d['anomalia']}{RESET}")
        else:
            print(f" Esperando datos del robot...")

        print(f"{'─'*55}")
        print(f" Muestras por clase:")
        for clase, cnt in _estado['muestras_clase'].items():
            semaforo = VERDE if cnt >= 100 else (AMARILLO if cnt >= 30 else ROJO)
            print(f"   {clase:20s}: {semaforo}{cnt:4d}{RESET}")
        print(f"{'─'*55}")
        print(f" [1-5] cambiar etiqueta  [r] resumen  [q] salir")

        time.sleep(0.5)


# =============================================================================
#  GRAFICADO EN TIEMPO REAL (matplotlib)
# =============================================================================

def iniciar_grafico():
    """Gráfico en tiempo real de las señales más importantes."""
    if not HAS_MATPLOTLIB:
        print("[WARN] matplotlib no disponible para gráfico en tiempo real")
        return

    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    fig.suptitle('Señales del Robot — Tiempo Real', fontsize=12)

    colores_clase_idx = {c: i for i, c in enumerate(list(CLASES.values()))}
    cmap = plt.cm.get_cmap('Set1', 5)

    def actualizar(frame):
        for ax in axes.flat:
            ax.clear()

        t = list(range(len(_buf_i_trac)))

        # Corrientes
        axes[0, 0].plot(t, list(_buf_i_trac), 'b-', linewidth=1,
                        label='Tracción')
        axes[0, 0].plot(t, list(_buf_i_cuch), 'r-', linewidth=1,
                        label='Cuchilla')
        axes[0, 0].set_title('Corriente (A)')
        axes[0, 0].legend(fontsize=8)
        axes[0, 0].set_ylim(0, 7)

        # Vibración
        axes[0, 1].plot(t, list(_buf_vib), 'g-', linewidth=1)
        axes[0, 1].set_title('Vibración RMS (m/s²)')
        axes[0, 1].set_ylim(0, 8)

        # Slip
        axes[1, 0].plot(t, list(_buf_slip), color='orange', linewidth=1)
        axes[1, 0].set_title('Slip ruedas (0–1)')
        axes[1, 0].set_ylim(0, 1)

        # Clase activa (texto centrado)
        axes[1, 1].axis('off')
        clase_act = _estado['etiqueta_actual']
        axes[1, 1].text(0.5, 0.6, clase_act, transform=axes[1, 1].transAxes,
                        fontsize=18, ha='center', va='center', fontweight='bold',
                        color='#185FA5')
        axes[1, 1].text(0.5, 0.35, f"Total: {_estado['muestras_totales']}",
                        transform=axes[1, 1].transAxes,
                        fontsize=12, ha='center', color='#5F5E5A')
        axes[1, 1].set_title('Etiqueta activa')

        fig.tight_layout(rect=[0, 0, 1, 0.95])

    ani = animation.FuncAnimation(fig, actualizar, interval=500, cache_frame_data=False)
    plt.show()


# =============================================================================
#  PUNTO DE ENTRADA
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Recolector de datos del robot')
    parser.add_argument('--port',     type=str, default='/dev/ttyUSB0',
                        help='Puerto serie del Pico W')
    parser.add_argument('--salida',   type=str, default=None,
                        help='Archivo CSV de salida')
    parser.add_argument('--graficar', action='store_true',
                        help='Mostrar gráfico en tiempo real')
    args = parser.parse_args()

    # Nombre de archivo con timestamp
    if args.salida is None:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.salida = f'datos/datos_suelo_{ts}.csv'

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    print(f"[SALIDA] Guardando en: {args.salida}")

    # Abrir CSV
    lock = threading.Lock()
    f_csv = open(args.salida, 'w', newline='')
    writer = csv.DictWriter(f_csv, fieldnames=CAMPOS_CSV, extrasaction='ignore')
    writer.writeheader()

    # Lanzar hilos
    hilo_serie = threading.Thread(
        target=hilo_lector_serie, args=(args.port, writer, lock), daemon=True)
    hilo_serie.start()

    hilo_kb = threading.Thread(target=hilo_teclado, daemon=True)
    hilo_kb.start()

    hilo_tui = threading.Thread(target=loop_tui, daemon=True)
    hilo_tui.start()

    # Gráfico en el hilo principal (si se pidió)
    if args.graficar:
        iniciar_grafico()
    else:
        try:
            while _estado['corriendo']:
                time.sleep(0.5)
        except KeyboardInterrupt:
            _estado['corriendo'] = False

    _imprimir_resumen()
    f_csv.close()
    print(f"[LISTO] Datos guardados en: {args.salida}")
    print(f"[LISTO] Entrenar modelo: python3 entrenar_modelo.py --csv {args.salida}")


if __name__ == '__main__':
    main()
