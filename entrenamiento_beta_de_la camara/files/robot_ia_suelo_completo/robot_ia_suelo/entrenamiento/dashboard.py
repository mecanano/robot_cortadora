#!/usr/bin/env python3
# =============================================================================
#  dashboard.py — Visualización de telemetría del robot en tiempo real
#
#  Lee el archivo telemetria.csv del Pico W o un CSV histórico y muestra:
#    - Estado del suelo clasificado por IA
#    - Corrientes, vibración, slip
#    - Trayectoria recorrida (odometría)
#    - Anomalías detectadas
#
#  Uso:
#    python3 dashboard.py --csv datos/telemetria.csv --vivo
#    python3 dashboard.py --csv datos/telemetria_20250101.csv
# =============================================================================

import argparse
import time
from pathlib import Path

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import matplotlib.animation as animation
import numpy as np
import pandas as pd

# =============================================================================
#  CONFIGURACIÓN VISUAL
# =============================================================================

COLORES_CLASE = {
    'pasto_corto':    '#3B6D11',
    'pasto_alto':     '#BA7517',
    'suelo_blando':   '#D85A30',
    'tierra_firme':   '#185FA5',
    'superficie_dura':'#888780',
    'sin_datos':      '#CCCCCC',
    'sin_etiquetar':  '#CCCCCC',
}

ICONOS_CLASE = {
    'pasto_corto':    '🟢',
    'pasto_alto':     '🟡',
    'suelo_blando':   '🟠',
    'tierra_firme':   '🔵',
    'superficie_dura':'⬜',
    'sin_datos':      '⬛',
}

VENTANA = 300  # muestras en los gráficos de señales


# =============================================================================
#  CARGADOR DE DATOS
# =============================================================================

class CargadorTelemetria:
    def __init__(self, ruta_csv: str, modo_vivo: bool):
        self.ruta = Path(ruta_csv)
        self.vivo = modo_vivo
        self._n_leidas = 0
        self.df = pd.DataFrame()

    def actualizar(self):
        """Carga (o recarga) el CSV. En modo vivo solo lee filas nuevas."""
        try:
            df_nuevo = pd.read_csv(self.ruta, on_bad_lines='skip')
        except (FileNotFoundError, pd.errors.EmptyDataError):
            return

        if self.vivo:
            if len(df_nuevo) > self._n_leidas:
                self.df = df_nuevo.iloc[-VENTANA:]
                self._n_leidas = len(df_nuevo)
        else:
            self.df = df_nuevo

        # Asegurar columnas numéricas
        for col in ['i_trac', 'i_cuch', 'volt', 'rpm_L', 'rpm_R',
                    'vib_rms', 'slip_L', 'slip_R', 'pos_x', 'pos_y', 'theta',
                    'pwm_L', 'pwm_R', 'pwm_cuch']:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')


# =============================================================================
#  DASHBOARD
# =============================================================================

class Dashboard:
    def __init__(self, cargador: CargadorTelemetria):
        self.cargador = cargador

        # Layout
        self.fig = plt.figure(figsize=(16, 9), facecolor='#1a1a2e')
        gs = gridspec.GridSpec(3, 4, figure=self.fig,
                               hspace=0.4, wspace=0.35,
                               left=0.06, right=0.97,
                               top=0.93, bottom=0.06)

        self.ax_clase    = self.fig.add_subplot(gs[0, 0])
        self.ax_corriente= self.fig.add_subplot(gs[0, 1:3])
        self.ax_volt     = self.fig.add_subplot(gs[0, 3])
        self.ax_vib      = self.fig.add_subplot(gs[1, 0:2])
        self.ax_slip     = self.fig.add_subplot(gs[1, 2:4])
        self.ax_tray     = self.fig.add_subplot(gs[2, 0:2])
        self.ax_hist     = self.fig.add_subplot(gs[2, 2:4])

        self._estilo_fondo()

        self.fig.suptitle('ROBOT AUTÓNOMO DE CORTE — DASHBOARD IA',
                          color='white', fontsize=13, fontweight='bold',
                          y=0.97)

    def _estilo_fondo(self):
        bg_panel = '#16213e'
        for ax in [self.ax_clase, self.ax_corriente, self.ax_volt,
                   self.ax_vib, self.ax_slip, self.ax_tray, self.ax_hist]:
            ax.set_facecolor(bg_panel)
            ax.tick_params(colors='#aaaaaa', labelsize=8)
            for spine in ax.spines.values():
                spine.set_color('#333355')
            ax.title.set_color('#dddddd')

    def actualizar(self, frame):
        self.cargador.actualizar()
        df = self.cargador.df

        if df.empty:
            return

        df_ult = df.tail(VENTANA)
        ultimo = df.iloc[-1]

        # ─── Panel 1: Clase de suelo actual ───────────────────────────────
        ax = self.ax_clase
        ax.clear()
        ax.set_facecolor('#16213e')
        ax.axis('off')

        clase = str(ultimo.get('clase_suelo', 'sin_datos'))
        color = COLORES_CLASE.get(clase, '#CCCCCC')
        icono = ICONOS_CLASE.get(clase, '⬛')
        conf  = float(ultimo.get('confianza', 0) or 0)

        ax.add_patch(plt.Rectangle((0.05, 0.05), 0.9, 0.9,
                                   color=color, alpha=0.3,
                                   transform=ax.transAxes))
        ax.text(0.5, 0.65, clase.replace('_', '\n'),
                transform=ax.transAxes, fontsize=10, ha='center', va='center',
                color=color, fontweight='bold')
        ax.text(0.5, 0.30, f"confianza: {conf:.0%}",
                transform=ax.transAxes, fontsize=8, ha='center',
                color='#aaaaaa')
        ax.set_title('Clase de suelo (IA)', pad=4)

        # ─── Panel 2: Corrientes ──────────────────────────────────────────
        ax = self.ax_corriente
        ax.clear()
        ax.set_facecolor('#16213e')
        t = np.arange(len(df_ult))
        if 'i_trac' in df_ult.columns:
            ax.plot(t, df_ult['i_trac'].values, color='#5bc0eb',
                    linewidth=1.2, label='Tracción')
        if 'i_cuch' in df_ult.columns:
            ax.plot(t, df_ult['i_cuch'].values, color='#e05c5c',
                    linewidth=1.2, label='Cuchilla')
        ax.axhline(6.0, color='#e05c5c', linestyle='--', alpha=0.4, linewidth=0.8)
        ax.set_ylim(0, 8)
        ax.set_ylabel('A', color='#aaaaaa', fontsize=8)
        ax.set_title('Corriente de motores')
        ax.legend(fontsize=7, facecolor='#16213e', labelcolor='white',
                  framealpha=0.8)
        ax.tick_params(colors='#aaaaaa')
        for spine in ax.spines.values():
            spine.set_color('#333355')

        # ─── Panel 3: Voltaje batería ──────────────────────────────────────
        ax = self.ax_volt
        ax.clear()
        ax.set_facecolor('#16213e')
        volt = float(ultimo.get('volt', 0) or 0)
        porcentaje = max(0, min(1, (volt - 9.0) / (12.6 - 9.0)))
        color_v = '#3B6D11' if porcentaje > 0.5 else (
                  '#BA7517' if porcentaje > 0.25 else '#D85A30')
        ax.barh([''], [porcentaje], color=color_v, height=0.4)
        ax.barh([''], [1], color='#333355', height=0.4, zorder=0)
        ax.set_xlim(0, 1)
        ax.set_title(f'Batería: {volt:.1f} V', pad=4)
        ax.text(0.5, 0.3, f"{porcentaje:.0%}", transform=ax.transAxes,
                ha='center', color='white', fontsize=14, fontweight='bold')
        ax.axis('off')

        # ─── Panel 4: Vibración IMU ───────────────────────────────────────
        ax = self.ax_vib
        ax.clear()
        ax.set_facecolor('#16213e')
        if 'vib_rms' in df_ult.columns:
            vib = df_ult['vib_rms'].values
            ax.fill_between(np.arange(len(vib)), vib,
                            color='#9b5de5', alpha=0.6, linewidth=0)
            ax.plot(vib, color='#c77dff', linewidth=1)
        ax.axhline(3.5, color='#e05c5c', linestyle='--', alpha=0.5,
                   linewidth=0.8, label='umbral alto')
        ax.axhline(1.8, color='#BA7517', linestyle='--', alpha=0.5,
                   linewidth=0.8, label='umbral medio')
        ax.set_ylim(0, 8)
        ax.set_ylabel('m/s²', color='#aaaaaa', fontsize=8)
        ax.set_title('Vibración IMU (RMS)')
        ax.legend(fontsize=7, facecolor='#16213e', labelcolor='white')
        ax.tick_params(colors='#aaaaaa')
        for spine in ax.spines.values():
            spine.set_color('#333355')

        # ─── Panel 5: Slip ────────────────────────────────────────────────
        ax = self.ax_slip
        ax.clear()
        ax.set_facecolor('#16213e')
        if 'slip_L' in df_ult.columns:
            ax.plot(df_ult['slip_L'].values, color='#f9c74f',
                    linewidth=1.2, alpha=0.8, label='Izquierda')
        if 'slip_R' in df_ult.columns:
            ax.plot(df_ult['slip_R'].values, color='#f8961e',
                    linewidth=1.2, alpha=0.8, label='Derecha')
        ax.axhline(0.25, color='#e05c5c', linestyle='--', alpha=0.5,
                   linewidth=0.8, label='umbral')
        ax.set_ylim(0, 1)
        ax.set_ylabel('slip (0–1)', color='#aaaaaa', fontsize=8)
        ax.set_title('Slip de ruedas')
        ax.legend(fontsize=7, facecolor='#16213e', labelcolor='white')
        ax.tick_params(colors='#aaaaaa')
        for spine in ax.spines.values():
            spine.set_color('#333355')

        # ─── Panel 6: Trayectoria (odometría) ────────────────────────────
        ax = self.ax_tray
        ax.clear()
        ax.set_facecolor('#16213e')
        if 'pos_x' in df.columns and 'pos_y' in df.columns:
            x = df['pos_x'].dropna().values
            y = df['pos_y'].dropna().values
            if len(x) > 1:
                # Colorear por clase de suelo
                clases_tray = df.loc[df['pos_x'].notna(), 'clase_suelo'].values
                clases_tray = clases_tray[:len(x)]
                for i in range(len(x) - 1):
                    c = COLORES_CLASE.get(clases_tray[i] if i < len(clases_tray) else 'sin_datos', '#888')
                    ax.plot(x[i:i+2], y[i:i+2], color=c, linewidth=2, alpha=0.8)
                ax.plot(x[-1], y[-1], 'wo', markersize=8)  # posición actual
        ax.set_aspect('equal', 'box')
        ax.set_xlabel('X (m)', color='#aaaaaa', fontsize=8)
        ax.set_ylabel('Y (m)', color='#aaaaaa', fontsize=8)
        ax.set_title('Trayectoria (odometría)')
        ax.tick_params(colors='#aaaaaa')
        for spine in ax.spines.values():
            spine.set_color('#333355')

        # ─── Panel 7: Histograma clases detectadas ────────────────────────
        ax = self.ax_hist
        ax.clear()
        ax.set_facecolor('#16213e')
        if 'clase_suelo' in df.columns:
            conteos = df['clase_suelo'].value_counts()
            clases_ord = [c for c in COLORES_CLASE if c in conteos.index]
            valores = [conteos.get(c, 0) for c in clases_ord]
            colores_bar = [COLORES_CLASE[c] for c in clases_ord]
            bars = ax.barh(clases_ord, valores, color=colores_bar, alpha=0.85)
            for bar, val in zip(bars, valores):
                ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                        str(val), va='center', color='white', fontsize=8)
        ax.set_title('Distribución de clases (sesión)')
        ax.tick_params(colors='#aaaaaa', labelsize=8)
        for spine in ax.spines.values():
            spine.set_color('#333355')
        ax.set_facecolor('#16213e')


def main():
    parser = argparse.ArgumentParser(description='Dashboard de telemetría del robot')
    parser.add_argument('--csv',   type=str, default='telemetria.csv')
    parser.add_argument('--vivo',  action='store_true',
                        help='Actualizar en tiempo real mientras el robot corre')
    args = parser.parse_args()

    cargador = CargadorTelemetria(args.csv, modo_vivo=args.vivo)
    cargador.actualizar()

    dash = Dashboard(cargador)

    intervalo = 1000 if args.vivo else 5000
    ani = animation.FuncAnimation(
        dash.fig, dash.actualizar,
        interval=intervalo, cache_frame_data=False)

    plt.show()


if __name__ == '__main__':
    main()
