# Sistema de IA para Reconocimiento de Suelo
## Robot Autónomo de Corte — Documentación completa

---

## Arquitectura general

```
┌─────────────────────────────────────────────────────────────┐
│                  RASPBERRY PI PICO W                        │
│                                                             │
│  CORE 0 (tiempo real)        CORE 1 (alto nivel)            │
│  ────────────────────        ─────────────────────          │
│  Tarea 1: PID motores        Tarea 4: Navegación            │
│           200 Hz             Tarea 5: Telemetría            │
│  Tarea 2: Encoders           Tarea 6: Clasificador IA       │
│           200 Hz                      10 Hz                 │
│  Tarea 3: Sensores                                          │
│           100 Hz                                            │
│                                                             │
│         ▲         SharedBuffer (lock)         ▲             │
│         │                                     │             │
│  IBT-2 L/R  INA219×2  MPU-6050  HC-SR04  INA219            │
└─────────────────────────────────────────────────────────────┘
            │ USB/UART │ UART (telemetría)
            ▼                    ▼
    [MicroPython]           [PC - Python]
                             recolectar_datos.py
                             entrenar_modelo.py
                             dashboard.py
```

---

## Features del clasificador de suelo

| Feature | Sensor origen | Cálculo | Indica |
|---------|--------------|---------|--------|
| `i_traccion` | INA219 (0x40) | Directo | Resistencia mecánica del terreno |
| `i_cuchilla` | INA219 (0x41) | Directo | Densidad/altura de la vegetación |
| `slip` | Encoders + PWM | `1 - rpm_real/rpm_esperado` | Adherencia del suelo |
| `vib_rms` | MPU-6050 acelerómetro | RMS ventana 50 muestras | Textura/irregularidad del suelo |
| `pwm_ratio` | PWM + Encoders | `pwm / (rpm/150)` | Eficiencia de tracción |

---

## Clases de suelo y acciones

| Clase | Vel. tracción | PWM cuchilla | Sep. trayectorias | Cuándo aparece |
|-------|:---:|:---:|:---:|---|
| `pasto_corto` | 100% | 80% | 20 cm | Mantenimiento normal |
| `pasto_alto` | 55% | 100% | 15 cm | Pasto sin cortar o crecido |
| `suelo_blando` | 35% | 50% | 25 cm | Tierra húmeda, barro |
| `tierra_firme` | 90% | 70% | 20 cm | Tierra seca compacta |
| `superficie_dura` | 80% | 0% | 30 cm | Cemento, adoquines |

---

## Instalación

### En la PC

```bash
# Clonar / copiar el proyecto
cd robot_ia_suelo

# Instalar dependencias
pip install -r requirements.txt

# Verificar
python3 -c "import sklearn, numpy, pandas, serial; print('OK')"
```

### En el Pico W

1. Instalar MicroPython (UF2 oficial de micropython.org)
2. Instalar Thonny IDE o mpremote
3. Copiar archivos al Pico W:

```bash
# Con mpremote:
mpremote cp firmware/main.py :/main.py
mpremote cp model_umbrales.json :/model_umbrales.json   # después de entrenar

# O con Thonny: abrir archivo → Archivo → Guardar como → Dispositivo MicroPython
```

---

## Flujo de trabajo completo

### Paso 1: Primera ejecución (sin modelo entrenado)

El robot arranca con umbrales por defecto en `ClasificadorSuelo.UMBRALES`.
Funciona pero con menor precisión que el modelo entrenado.

```bash
# Flashear el firmware
mpremote cp firmware/main.py :/main.py
mpremote reset
```

### Paso 2: Recolección de datos

Correr el robot en todos los tipos de suelo disponibles:

```bash
python3 entrenamiento/recolectar_datos.py --port /dev/ttyUSB0
```

Controles durante la recolección:
- Tecla `1` → marcar como `pasto_corto` (robot cortando pasto normal)
- Tecla `2` → marcar como `pasto_alto` (robot en pasto sin cortar)
- Tecla `3` → marcar como `suelo_blando` (tierra húmeda, barro)
- Tecla `4` → marcar como `tierra_firme` (tierra seca)
- Tecla `5` → marcar como `superficie_dura` (cemento, baldosa)
- Tecla `r` → ver resumen de muestras
- Tecla `q` → salir

**Objetivo**: al menos 100 muestras por clase (recomendado: 300+).

### Paso 3: Entrenar el modelo

```bash
python3 entrenamiento/entrenar_modelo.py \
    --csv datos/datos_suelo_20250101_120000.csv \
    --graficar

# Sin datos reales (prueba con datos sintéticos):
python3 entrenamiento/entrenar_modelo.py --sintetico --graficar
```

El script genera `model_umbrales.json` con los umbrales calibrados.

### Paso 4: Desplegar al robot

```bash
mpremote cp model_umbrales.json :/model_umbrales.json
mpremote reset
```

El firmware carga automáticamente el JSON al iniciar.

### Paso 5: Monitorear

```bash
# Dashboard en tiempo real
python3 entrenamiento/dashboard.py \
    --csv telemetria.csv --vivo

# Recuperar CSV de telemetría del Pico W
mpremote cp :/telemetria.csv datos/telemetria_sesion1.csv
```

---

## Estructura de archivos

```
robot_ia_suelo/
│
├── firmware/
│   └── main.py                  # Firmware completo del Pico W
│
├── entrenamiento/
│   ├── entrenar_modelo.py       # Pipeline de entrenamiento
│   ├── recolectar_datos.py      # Captura de datos con etiquetado
│   └── dashboard.py             # Visualización de telemetría
│
├── datos/
│   └── datos_suelo_*.csv        # Datos recolectados del robot
│
├── model_umbrales.json          # Modelo exportado (copiar al Pico W)
├── modelo_sklearn.joblib        # Modelo sklearn (para re-entrenamiento)
└── requirements.txt
```

---

## Diagnóstico y calibración

### El robot clasifica mal el suelo

1. Ver el gráfico de importancia de features en `analisis_clasificador.png`
2. Si `slip` tiene poca importancia → ajustar `rpm_a_pwm_factor` en `LectorEncoders.calcular_slip()`
3. Si `vib_rms` siempre es bajo → aumentar la ganancia del IMU o revisar montaje
4. Recolectar más muestras de las clases con menor F1

### El slip siempre da 0

Calibrar el factor RPM/PWM:
```python
# En main.py, LectorEncoders.calcular_slip():
rpm_esperado = abs(pwm_aplicado) * 150.0   # ← cambiar 150.0 por el valor real
# El valor real = RPM máximo de tu motor a PWM=1.0
# Medirlo con: correr el motor sin carga y leer RPM con el encoder
```

### El clasificador cambia demasiado rápido

Aumentar el historial de suavizado en `ClasificadorSuelo.__init__()`:
```python
self._HIST_LEN = 10   # ← default: 5. Más lento pero más estable
```

### Anomalía BLOQUEO_CUCHILLA frecuente

Ajustar el umbral de corriente:
```python
# En main.py:
LIMITE_CORRIENTE_CUCH_A = 5.0   # ← bajar si el motor consume menos
```

---

## Protocolo serie (Pico W → PC)

El Pico W envía una línea JSON por UART cada 500 ms (Tarea 5):

```json
{
  "ts": 12345,
  "i_trac": 1.23, "i_cuch": 0.85,
  "volt": 11.9,
  "rpm_L": 78.5, "rpm_R": 79.1,
  "pwm_L": 0.51, "pwm_R": 0.52,
  "ax": 0.1, "ay": -0.2, "az": 9.8, "gz": 0.01,
  "vib": 1.3,
  "dist": 99.0,
  "px": 0.5, "py": 1.2, "th": 0.05,
  "clase": "pasto_corto",
  "conf": 0.85,
  "anom": ""
}
```

---

## Conexiones de hardware

| Pico W Pin | Señal | Componente |
|:---:|---|---|
| GP0 | MOT_L_PWM_FWD | IBT-2 izquierdo |
| GP1 | MOT_L_PWM_REV | IBT-2 izquierdo |
| GP2 | MOT_R_PWM_FWD | IBT-2 derecho |
| GP3 | MOT_R_PWM_REV | IBT-2 derecho |
| GP4 | CUCHILLA_PWM | Driver cuchilla |
| GP5 | CUCHILLA_EN | Driver cuchilla |
| GP6 | ENC_L_A | Encoder rueda izquierda |
| GP7 | ENC_L_B | Encoder rueda izquierda |
| GP8 | ENC_R_A | Encoder rueda derecha |
| GP9 | ENC_R_B | Encoder rueda derecha |
| GP10 | ULTRAS_TRIG | HC-SR04 |
| GP11 | ULTRAS_ECHO | HC-SR04 |
| GP15 | E-STOP | Botón emergencia (pull-up) |
| GP16 | SENSOR_ELEVACION | Switch elevación |
| GP20 | I2C_SDA | MPU-6050 + INA219×2 |
| GP21 | I2C_SCL | MPU-6050 + INA219×2 |

**Direcciones I2C:**
- MPU-6050: `0x68` (AD0 a GND)
- INA219 tracción: `0x40` (A0=GND, A1=GND)
- INA219 cuchilla: `0x41` (A0=VCC, A1=GND)
