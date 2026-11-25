#!/usr/bin/env python3
# =============================================================================
#  entrenar_modelo.py — Pipeline completo de entrenamiento
#  Corre en la PC. Genera model_umbrales.json para copiar al Pico W.
#
#  Uso:
#    python3 entrenar_modelo.py --csv datos/datos_suelo.csv
#    python3 entrenar_modelo.py --csv datos/datos_suelo.csv --graficar
# =============================================================================

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import (classification_report, confusion_matrix,
                             ConfusionMatrixDisplay)
from sklearn.preprocessing import StandardScaler
import joblib

# Graficado opcional
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# =============================================================================
#  CONFIGURACIÓN
# =============================================================================

CLASES = ['pasto_corto', 'pasto_alto', 'suelo_blando',
          'tierra_firme', 'superficie_dura']

COLORES_CLASE = {
    'pasto_corto':    '#3B6D11',
    'pasto_alto':     '#BA7517',
    'suelo_blando':   '#D85A30',
    'tierra_firme':   '#185FA5',
    'superficie_dura':'#5F5E5A',
}

# Features que usa el clasificador embebido
FEATURES_USADAS = ['i_traccion', 'i_cuchilla', 'slip', 'vib_rms', 'pwm_ratio']

# =============================================================================
#  PASO 1: INGENIERÍA DE FEATURES
# =============================================================================

def calcular_slip(rpm_real: pd.Series, pwm: pd.Series,
                  rpm_a_pwm_factor: float = 150.0) -> pd.Series:
    """
    Calcula el slip de las ruedas.
    slip = 0   → rueda girando exactamente como se espera
    slip = 1   → rueda completamente patinando
    slip < 0   → rueda girando más rápido de lo esperado (cuesta abajo)
    """
    rpm_esperado = pwm.abs() * rpm_a_pwm_factor
    slip = 1.0 - (rpm_real.abs() / rpm_esperado.clip(lower=0.1))
    return slip.clip(-0.5, 1.0)


def calcular_pwm_ratio(pwm: pd.Series, rpm: pd.Series) -> pd.Series:
    """
    Ratio entre PWM aplicado y velocidad resultante.
    Alto = mucho esfuerzo, poca velocidad → suelo resistente o blando.
    """
    return pwm.abs() / (rpm.abs() / 150.0).clip(lower=0.01)


def calcular_vib_rms(df: pd.DataFrame,
                     ventana: int = 50) -> pd.Series:
    """
    Vibración RMS del IMU en ventana deslizante.
    Usa la magnitud de la aceleración menos la gravedad.
    """
    G = 9.80665
    mag = np.sqrt(df['accel_x']**2 + df['accel_y']**2 + df['accel_z']**2) - G
    vib_rms = mag.rolling(ventana, min_periods=1).apply(
        lambda x: math.sqrt(np.mean(x**2))
    )
    return vib_rms


def preparar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construye el dataframe de features a partir de datos crudos del robot.
    Las columnas de entrada esperadas son:
        timestamp, i_traccion, i_cuchilla, rpm_L, rpm_R,
        accel_x, accel_y, accel_z, pwm_L, pwm_R, voltaje, etiqueta
    """
    print("[FEATURES] Calculando features derivadas...")

    df = df.copy()

    # Promedios de ruedas
    df['rpm_prom'] = (df['rpm_L'].abs() + df['rpm_R'].abs()) / 2
    df['pwm_prom'] = (df['pwm_L'].abs() + df['pwm_R'].abs()) / 2

    # Slip promedio
    slip_L = calcular_slip(df['rpm_L'], df['pwm_L'])
    slip_R = calcular_slip(df['rpm_R'], df['pwm_R'])
    df['slip'] = (slip_L + slip_R) / 2

    # Ratio PWM/velocidad
    df['pwm_ratio'] = calcular_pwm_ratio(df['pwm_prom'], df['rpm_prom'])

    # Vibración RMS
    df['vib_rms'] = calcular_vib_rms(df)

    # Suavizado de corrientes (media móvil 5 muestras)
    df['i_traccion'] = df['i_traccion'].rolling(5, min_periods=1).mean()
    df['i_cuchilla'] = df['i_cuchilla'].rolling(5, min_periods=1).mean()

    # Eliminar filas con NaN y etiqueta inválida
    df = df.dropna(subset=FEATURES_USADAS + ['etiqueta'])
    df = df[df['etiqueta'].isin(CLASES)]

    print(f"[FEATURES] Muestras totales: {len(df)}")
    print(f"[FEATURES] Distribución de clases:")
    for clase, cnt in df['etiqueta'].value_counts().items():
        print(f"            {clase:20s}: {cnt:4d} muestras")

    return df


# =============================================================================
#  PASO 2: ENTRENAMIENTO
# =============================================================================

def entrenar(df: pd.DataFrame, usar_random_forest: bool = False):
    """
    Entrena el clasificador. Devuelve (modelo, X_test, y_test, scaler).
    
    Se entrena un árbol de decisión (para embeber en Pico W) y
    opcionalmente un Random Forest (para comparar accuracy).
    """
    X = df[FEATURES_USADAS].values
    y = df['etiqueta'].values

    # Codificar etiquetas a enteros
    y_int = np.array([CLASES.index(c) for c in y])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_int, test_size=0.2, random_state=42, stratify=y_int
    )

    print(f"\n[ENTRENAMIENTO] Train: {len(X_train)} | Test: {len(X_test)}")

    # --- Árbol de decisión (embebible) ---
    print("[ENTRENAMIENTO] Entrenando DecisionTreeClassifier...")
    dt = DecisionTreeClassifier(
        max_depth=8,           # profundidad máxima — equilibrio complejidad/tamaño
        min_samples_leaf=5,    # evitar sobreajuste con pocas muestras
        criterion='gini',
        class_weight='balanced',  # compensar clases desbalanceadas
        random_state=42
    )
    dt.fit(X_train, y_train)

    # Validación cruzada
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores_dt = cross_val_score(dt, X, y_int, cv=cv, scoring='f1_weighted')
    print(f"[DT] F1 CV (5-fold): {scores_dt.mean():.3f} ± {scores_dt.std():.3f}")
    print(f"[DT] Accuracy test:  {dt.score(X_test, y_test):.3f}")
    print(f"[DT] Profundidad real: {dt.get_depth()} | Hojas: {dt.get_n_leaves()}")

    # --- Random Forest (solo comparación, no se embebe) ---
    if usar_random_forest:
        print("[ENTRENAMIENTO] Entrenando RandomForestClassifier...")
        rf = RandomForestClassifier(
            n_estimators=50, max_depth=8, class_weight='balanced',
            random_state=42, n_jobs=-1
        )
        rf.fit(X_train, y_train)
        scores_rf = cross_val_score(rf, X, y_int, cv=cv, scoring='f1_weighted')
        print(f"[RF] F1 CV (5-fold): {scores_rf.mean():.3f} ± {scores_rf.std():.3f}")
        print(f"[RF] Accuracy test:  {rf.score(X_test, y_test):.3f}")

    return dt, X_test, y_test, None  # sin scaler (árbol no necesita normalizar)


# =============================================================================
#  PASO 3: ANÁLISIS Y VISUALIZACIÓN
# =============================================================================

def analizar_modelo(modelo, X_test, y_test, df: pd.DataFrame):
    """Imprime reporte completo y muestra gráficos si matplotlib disponible."""

    y_pred = modelo.predict(X_test)

    print("\n" + "="*60)
    print("REPORTE DE CLASIFICACIÓN")
    print("="*60)
    print(classification_report(y_test, y_pred,
                                 target_names=CLASES, zero_division=0))

    # Importancia de features
    print("\nIMPORTANCIA DE FEATURES:")
    importancias = sorted(zip(FEATURES_USADAS, modelo.feature_importances_),
                          key=lambda x: -x[1])
    for feat, imp in importancias:
        barra = '█' * int(imp * 40)
        print(f"  {feat:15s}: {barra} {imp:.4f}")

    if HAS_MATPLOTLIB:
        _graficar_todo(modelo, X_test, y_test, y_pred, df)


def _graficar_todo(modelo, X_test, y_test, y_pred, df):
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.suptitle('Análisis del Clasificador de Suelo — Robot Autónomo',
                 fontsize=14, fontweight='bold')
    colores = [COLORES_CLASE[c] for c in CLASES]

    # 1) Matriz de confusión
    ax = axes[0, 0]
    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(cm, display_labels=CLASES)
    disp.plot(ax=ax, colorbar=False, cmap='Blues')
    ax.set_title('Matriz de confusión')
    plt.setp(ax.get_xticklabels(), rotation=30, ha='right', fontsize=8)
    plt.setp(ax.get_yticklabels(), fontsize=8)

    # 2) Importancia de features
    ax = axes[0, 1]
    imp = modelo.feature_importances_
    ax.barh(FEATURES_USADAS, imp, color='#185FA5', alpha=0.8)
    ax.set_xlabel('Importancia (Gini)')
    ax.set_title('Importancia de features')

    # 3) Distribución de clases en el dataset
    ax = axes[0, 2]
    conteos = df['etiqueta'].value_counts()
    ax.bar(conteos.index, conteos.values,
           color=[COLORES_CLASE.get(c, '#888') for c in conteos.index])
    ax.set_title('Muestras por clase')
    plt.setp(ax.get_xticklabels(), rotation=30, ha='right', fontsize=8)

    # 4) Scatter: i_traccion vs i_cuchilla coloreado por clase
    ax = axes[1, 0]
    for i, clase in enumerate(CLASES):
        mask = df['etiqueta'] == clase
        ax.scatter(df.loc[mask, 'i_traccion'], df.loc[mask, 'i_cuchilla'],
                   c=COLORES_CLASE[clase], label=clase, alpha=0.5, s=10)
    ax.set_xlabel('Corriente tracción (A)')
    ax.set_ylabel('Corriente cuchilla (A)')
    ax.set_title('Corrientes por clase')
    ax.legend(fontsize=7)

    # 5) Scatter: slip vs vib_rms
    ax = axes[1, 1]
    for i, clase in enumerate(CLASES):
        mask = df['etiqueta'] == clase
        ax.scatter(df.loc[mask, 'slip'], df.loc[mask, 'vib_rms'],
                   c=COLORES_CLASE[clase], label=clase, alpha=0.5, s=10)
    ax.set_xlabel('Slip (0–1)')
    ax.set_ylabel('Vibración RMS (m/s²)')
    ax.set_title('Slip vs Vibración por clase')
    ax.legend(fontsize=7)

    # 6) Reglas del árbol (texto)
    ax = axes[1, 2]
    ax.axis('off')
    reglas_txt = export_text(modelo, feature_names=FEATURES_USADAS,
                             max_depth=4)
    ax.text(0.01, 0.99, reglas_txt[:800],
            transform=ax.transAxes, fontsize=6,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='#f5f5f5', alpha=0.8))
    ax.set_title('Árbol (primeros 4 niveles)')

    plt.tight_layout()
    plt.savefig('analisis_clasificador.png', dpi=150, bbox_inches='tight')
    print("[GRAFICOS] Guardado: analisis_clasificador.png")
    plt.show()


# =============================================================================
#  PASO 4: EXPORTAR PARA PICO W
# =============================================================================

def exportar_para_pico(modelo, salida_json: str = 'model_umbrales.json'):
    """
    Exporta los umbrales críticos del árbol de decisión como JSON liviano.
    El firmware del Pico W los carga en ClasificadorSuelo._cargar_modelo_flash().
    
    También exporta el árbol completo como lista de nodos para la versión
    genérica del predict() si se prefiere usar el árbol exactamente.
    """
    tree = modelo.tree_

    # --- Exportar umbrales clave (para la lógica if/elif del firmware) ---
    # Extrae los umbrales de cada feature del árbol entrenado
    umbrales_por_feature = {}
    for i in range(tree.node_count):
        if tree.children_left[i] != -1:  # nodo interno
            feat_idx = tree.feature[i]
            feat_name = FEATURES_USADAS[feat_idx]
            thresh = float(tree.threshold[i])
            if feat_name not in umbrales_por_feature:
                umbrales_por_feature[feat_name] = []
            umbrales_por_feature[feat_name].append(round(thresh, 4))

    # Tomar el umbral más representativo (mediana) por feature
    umbrales_resumen = {}
    for feat, vals in umbrales_por_feature.items():
        vals_sorted = sorted(vals)
        mid = len(vals_sorted) // 2
        # Tomar mediana y el siguiente — para umbrales alto/medio
        umbrales_resumen[feat + '_alto']  = vals_sorted[min(-1, -1)]
        umbrales_resumen[feat + '_medio'] = vals_sorted[mid]

    # Renombrar a los nombres que usa el firmware
    umbrales_fw = {
        'i_trac_alto':    umbrales_resumen.get('i_traccion_alto',  3.5),
        'i_trac_medio':   umbrales_resumen.get('i_traccion_medio', 2.0),
        'i_cuch_alto':    umbrales_resumen.get('i_cuchilla_alto',  2.5),
        'i_cuch_medio':   umbrales_resumen.get('i_cuchilla_medio', 1.2),
        'slip_alto':      umbrales_resumen.get('slip_alto',        0.25),
        'slip_medio':     umbrales_resumen.get('slip_medio',       0.10),
        'vib_alta':       umbrales_resumen.get('vib_rms_alto',     3.5),
        'vib_media':      umbrales_resumen.get('vib_rms_medio',    1.8),
        'pwm_ratio_alto': umbrales_resumen.get('pwm_ratio_alto',   1.4),
    }

    # --- Exportar árbol completo como nodos (para predict() genérico) ---
    nodos = []
    for i in range(tree.node_count):
        if tree.children_left[i] == -1:
            nodos.append({
                'leaf': True,
                'class': int(np.argmax(tree.value[i]))
            })
        else:
            nodos.append({
                'leaf': False,
                'feat': int(tree.feature[i]),
                'thresh': round(float(tree.threshold[i]), 4),
                'left': int(tree.children_left[i]),
                'right': int(tree.children_right[i])
            })

    exportacion = {
        'version':    '1.0',
        'clases':     CLASES,
        'features':   FEATURES_USADAS,
        'umbrales':   umbrales_fw,
        'nodos':      nodos,
        'metadata': {
            'n_nodos':  tree.node_count,
            'depth':    int(modelo.get_depth()),
            'n_hojas':  int(modelo.get_n_leaves()),
        }
    }

    with open(salida_json, 'w') as f:
        json.dump(exportacion, f, indent=2)

    tam_bytes = os.path.getsize(salida_json)
    print(f"\n[EXPORT] Guardado: {salida_json} ({tam_bytes} bytes)")
    print(f"[EXPORT] Nodos del árbol: {tree.node_count}")
    print(f"[EXPORT] Copiar este archivo al Pico W con Thonny o mpremote")

    return salida_json


# =============================================================================
#  GENERADOR DE DATOS SINTÉTICOS (para prueba sin robot físico)
# =============================================================================

def generar_datos_sinteticos(n_por_clase: int = 200,
                              ruido: float = 0.15) -> pd.DataFrame:
    """
    Genera datos sintéticos realistas para probar el pipeline de entrenamiento.
    
    Basados en las características físicas esperadas de cada tipo de suelo.
    Reemplazar con datos reales del robot para el modelo de producción.
    """
    np.random.seed(42)
    filas = []

    # Parámetros base por clase: [i_trac, i_cuch, slip, vib, pwm_ratio]
    params = {
        'pasto_corto':    [1.4, 1.0, 0.05, 1.2, 0.80],
        'pasto_alto':     [2.2, 3.2, 0.08, 2.2, 1.00],
        'suelo_blando':   [4.2, 1.1, 0.35, 3.8, 1.65],
        'tierra_firme':   [1.7, 1.0, 0.04, 1.5, 0.85],
        'superficie_dura':[0.7, 0.2, 0.02, 0.4, 0.55],
    }

    for clase, (it, ic, slip, vib, pwm) in params.items():
        for _ in range(n_por_clase):
            r = np.random.normal
            filas.append({
                'timestamp':  np.random.uniform(0, 10000),
                'i_traccion': max(0, r(it,   it * ruido)),
                'i_cuchilla': max(0, r(ic,   ic * ruido)),
                'rpm_L':      max(0, r(80.0, 15.0)),
                'rpm_R':      max(0, r(80.0, 15.0)),
                'accel_x':    r(0.0, 0.5),
                'accel_y':    r(0.0, 0.5),
                'accel_z':    r(9.8, 0.3),
                'pwm_L':      max(0, r(pwm * 0.5, 0.1)),
                'pwm_R':      max(0, r(pwm * 0.5, 0.1)),
                'voltaje':    r(11.8, 0.2),
                'etiqueta':   clase,
                # Features pre-calculadas (simuladas)
                'slip':       max(0, min(1, r(slip, slip * ruido + 0.02))),
                'vib_rms':    max(0, r(vib, vib * ruido)),
                'pwm_ratio':  max(0, r(pwm,  pwm * ruido)),
            })

    df = pd.DataFrame(filas)
    print(f"[SINTETICO] Generados {len(df)} registros sintéticos")
    return df


# =============================================================================
#  SCRIPT PRINCIPAL
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Entrena el clasificador de suelo para el robot autónomo')
    parser.add_argument('--csv',      type=str, default=None,
                        help='CSV con datos reales del robot')
    parser.add_argument('--sintetico', action='store_true',
                        help='Usar datos sintéticos (para prueba)')
    parser.add_argument('--graficar',  action='store_true',
                        help='Mostrar gráficos de análisis')
    parser.add_argument('--salida',   type=str, default='model_umbrales.json',
                        help='Archivo JSON de salida para el Pico W')
    parser.add_argument('--rf',       action='store_true',
                        help='Comparar con Random Forest')
    args = parser.parse_args()

    print("=" * 60)
    print("PIPELINE DE ENTRENAMIENTO — CLASIFICADOR DE SUELO")
    print("Robot Autónomo de Corte — IA v2.0")
    print("=" * 60)

    # --- Cargar datos ---
    if args.csv:
        print(f"[DATOS] Cargando: {args.csv}")
        df_crudo = pd.read_csv(args.csv)
        df = preparar_features(df_crudo)
    elif args.sintetico:
        print("[DATOS] Usando datos sintéticos (modo prueba)")
        df = generar_datos_sinteticos(n_por_clase=300)
    else:
        print("[DATOS] No se especificó CSV. Usando datos sintéticos.")
        print("[DATOS] Para datos reales: --csv datos/datos_suelo.csv")
        df = generar_datos_sinteticos(n_por_clase=300)

    if len(df) < 50:
        print("[ERROR] Dataset muy pequeño. Necesitás al menos 50 muestras.")
        sys.exit(1)

    # --- Entrenar ---
    modelo, X_test, y_test, _ = entrenar(df, usar_random_forest=args.rf)

    # --- Analizar ---
    if args.graficar and HAS_MATPLOTLIB:
        analizar_modelo(modelo, X_test, y_test, df)
    elif args.graficar and not HAS_MATPLOTLIB:
        print("[WARN] matplotlib no instalado. Instalar con: pip install matplotlib")
    else:
        y_pred = modelo.predict(X_test)
        print("\n" + classification_report(y_test, y_pred,
                                           target_names=CLASES, zero_division=0))

    # --- Exportar ---
    exportar_para_pico(modelo, salida_json=args.salida)

    # --- Guardar modelo sklearn (para re-uso) ---
    joblib.dump(modelo, 'modelo_sklearn.joblib')
    print("[EXPORT] Modelo sklearn guardado: modelo_sklearn.joblib")

    print("\n[LISTO] Próximos pasos:")
    print("  1. Copiar model_umbrales.json al Pico W")
    print("     mpremote cp model_umbrales.json :/model_umbrales.json")
    print("  2. Resetear el Pico W — el firmware carga el modelo automáticamente")
    print("  3. Verificar en telemetría.csv que clase_suelo cambie según el terreno")


if __name__ == '__main__':
    main()
