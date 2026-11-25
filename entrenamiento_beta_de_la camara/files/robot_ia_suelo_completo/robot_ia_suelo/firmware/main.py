# =============================================================================
#  main.py — Firmware principal del robot autónomo de corte
#  Hardware: Raspberry Pi Pico W (RP2040, MicroPython)
#  Autor:    Tu proyecto de robot autónomo
#  Version:  2.0 — con IA de reconocimiento de suelo integrada
# =============================================================================
#
#  ARQUITECTURA DE TAREAS (dual-core):
#
#  CORE 0 — tareas de tiempo real
#    Tarea 1: control_motores()     200 Hz  — PID + IBT-2 PWM
#    Tarea 2: leer_encoders()       200 Hz  — RPM_L, RPM_R
#    Tarea 3: leer_sensores()       100 Hz  — IMU, INA219, ultrasonido
#
#  CORE 1 — tareas de alto nivel
#    Tarea 4: navegacion()           20 Hz  — cobertura adaptativa
#    Tarea 5: telemetria()            2 Hz  — registro en flash
#    Tarea 6: clasificador_suelo()   10 Hz  — IA árbol de decisión
#
#  BUFFER COMPARTIDO: SharedBuffer — acceso atómico entre cores
#
# =============================================================================

import utime
import _thread
import machine
import json
from machine import Pin, PWM, I2C, UART
import math

# =============================================================================
#  CONFIGURACIÓN DE PINES (ajustar según tu cableado)
# =============================================================================

# --- Motores de tracción (IBT-2 / BTS7960) ---
# Motor izquierdo
PIN_MOT_L_PWM_FWD  = 0   # GP0 → L_PWM_FWD
PIN_MOT_L_PWM_REV  = 1   # GP1 → L_PWM_REV
# Motor derecho
PIN_MOT_R_PWM_FWD  = 2   # GP2 → R_PWM_FWD
PIN_MOT_R_PWM_REV  = 3   # GP3 → R_PWM_REV

# --- Motor cuchilla ---
PIN_CUCHILLA_PWM   = 4   # GP4 → señal PWM cuchilla
PIN_CUCHILLA_EN    = 5   # GP5 → enable cuchilla

# --- Encoders ---
PIN_ENC_L_A        = 6   # GP6
PIN_ENC_L_B        = 7   # GP7
PIN_ENC_R_A        = 8   # GP8
PIN_ENC_R_B        = 9   # GP9

# --- Ultrasonido (HC-SR04) ---
PIN_ULTRAS_TRIG    = 10  # GP10
PIN_ULTRAS_ECHO    = 11  # GP11

# --- Seguridad ---
PIN_ESTOP          = 15  # GP15 — botón E-STOP (pull-up, activo LOW)
PIN_ELEVACION      = 16  # GP16 — sensor elevación (activo LOW)

# --- I2C (IMU + INA219) ---
I2C_SDA            = 20  # GP20
I2C_SCL            = 21  # GP21
I2C_FREQ           = 400_000

# Direcciones I2C
ADDR_IMU_MPU6050   = 0x68
ADDR_INA219_TRAC   = 0x40  # INA219 motores tracción
ADDR_INA219_CUCH   = 0x41  # INA219 motor cuchilla

# --- UART para telemetría/debug ---
PIN_UART_TX        = 0   # GP0 (UART0) — alternativo si no usás I2C en esos pines
PIN_UART_RX        = 1   # GP1

# =============================================================================
#  PARÁMETROS DEL ROBOT
# =============================================================================

# Mecánicos
RADIO_RUEDA_M      = 0.10   # 10 cm
DISTANCIA_EJES_M   = 0.35   # 35 cm entre ruedas
PULSOS_POR_REV     = 20     # encoder: pulsos por revolución completa

# PID motores — valores iniciales (ajustar en calibración)
PID_KP             = 1.2
PID_KI             = 0.4
PID_KD             = 0.05
PID_FREQ_HZ        = 200

# Seguridad
LIMITE_CORRIENTE_TRAC_A  = 6.0   # A — apagar si supera esto
LIMITE_CORRIENTE_CUCH_A  = 5.0   # A
VOLTAJE_BATERIA_MIN_V    = 10.5  # V — detener robot

# Cuchilla
CUCHILLA_PWM_BASE  = 0.75   # 75% en condiciones normales
CUCHILLA_ARRANQUE  = 0.3    # arranque suave en 300 ms

# =============================================================================
#  BUFFER COMPARTIDO ENTRE CORES
#  Acceso con lock para evitar race conditions
# =============================================================================

_lock = _thread.allocate_lock()

_shared = {
    # --- Sensores (escritura: core 0, lectura: core 0 y 1) ---
    'rpm_L':          0.0,
    'rpm_R':          0.0,
    'pos_x':          0.0,
    'pos_y':          0.0,
    'theta':          0.0,
    'i_traccion':     0.0,
    'i_cuchilla':     0.0,
    'voltaje':        12.0,
    'accel_x':        0.0,
    'accel_y':        0.0,
    'accel_z':        9.8,
    'giro_z':         0.0,
    'vib_rms':        0.0,
    'distancia_cm':   999.0,
    'pwm_L_actual':   0.0,
    'pwm_R_actual':   0.0,
    # --- Control (escritura: core 1 navegación, lectura: core 0 PID) ---
    'vel_target_L':   0.0,   # m/s objetivo rueda izquierda
    'vel_target_R':   0.0,   # m/s objetivo rueda derecha
    'pwm_cuchilla':   0.0,   # 0.0–1.0
    # --- IA suelo (escritura: core 1 clasificador, lectura: core 1 navegación) ---
    'clase_suelo':    'sin_datos',
    'confianza_suelo': 0.0,
    'accion_vel':     1.0,   # multiplicador velocidad
    'accion_sep_cm':  20.0,  # separación trayectorias
    # --- Estado del sistema ---
    'estop':          False,
    'elevado':        False,
    'modo':           'IDLE',  # IDLE, CORTANDO, EVITANDO, EMERGENCIA
    'anomalia':       None,
    'ts':             0,
}


def shared_read(key):
    with _lock:
        return _shared[key]


def shared_write(key, value):
    with _lock:
        _shared[key] = value


def shared_read_multi(keys):
    with _lock:
        return {k: _shared[k] for k in keys}


def shared_write_multi(data: dict):
    with _lock:
        _shared.update(data)


# =============================================================================
#  TAREA 1: CONTROL DE MOTORES  (core 0, 200 Hz)
# =============================================================================

class ControladorPID:
    """PID digital con anti-windup y límite de derivada."""

    def __init__(self, kp, ki, kd, freq_hz, out_min=-1.0, out_max=1.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = 1.0 / freq_hz
        self.out_min = out_min
        self.out_max = out_max
        self.integral = 0.0
        self.error_prev = 0.0
        self.integral_max = 0.5  # anti-windup

    def reset(self):
        self.integral = 0.0
        self.error_prev = 0.0

    def calcular(self, setpoint, medido):
        error = setpoint - medido
        # Proporcional
        p = self.kp * error
        # Integral con anti-windup
        self.integral += error * self.dt
        self.integral = max(-self.integral_max,
                            min(self.integral_max, self.integral))
        i = self.ki * self.integral
        # Derivativa (sobre la medición, no el error → evita derivative kick)
        d = -self.kd * (medido - self.error_prev) / self.dt
        self.error_prev = medido

        salida = p + i + d
        return max(self.out_min, min(self.out_max, salida))


class ControlMotores:
    """Maneja los 4 canales PWM del IBT-2 y el motor de cuchilla."""

    FREQ_PWM = 20_000  # 20 kHz — fuera del rango audible

    def __init__(self):
        self.pwm_L_fwd = PWM(Pin(PIN_MOT_L_PWM_FWD))
        self.pwm_L_rev = PWM(Pin(PIN_MOT_L_PWM_REV))
        self.pwm_R_fwd = PWM(Pin(PIN_MOT_R_PWM_FWD))
        self.pwm_R_rev = PWM(Pin(PIN_MOT_R_PWM_REV))
        self.pwm_cuch  = PWM(Pin(PIN_CUCHILLA_PWM))
        self.en_cuch   = Pin(PIN_CUCHILLA_EN, Pin.OUT)

        for pwm in [self.pwm_L_fwd, self.pwm_L_rev,
                    self.pwm_R_fwd, self.pwm_R_rev, self.pwm_cuch]:
            pwm.freq(self.FREQ_PWM)

        self.en_cuch.value(0)
        self._set_motor_L(0.0)
        self._set_motor_R(0.0)
        self._set_cuchilla(0.0)

        self.pid_L = ControladorPID(PID_KP, PID_KI, PID_KD, PID_FREQ_HZ)
        self.pid_R = ControladorPID(PID_KP, PID_KI, PID_KD, PID_FREQ_HZ)

    def _duty(self, val):
        """Convierte 0.0–1.0 a duty cycle 16-bit."""
        return int(max(0.0, min(1.0, val)) * 65535)

    def _set_motor_L(self, valor):
        """valor: -1.0 (rev) a +1.0 (fwd)"""
        if valor >= 0:
            self.pwm_L_fwd.duty_u16(self._duty(valor))
            self.pwm_L_rev.duty_u16(0)
        else:
            self.pwm_L_fwd.duty_u16(0)
            self.pwm_L_rev.duty_u16(self._duty(-valor))

    def _set_motor_R(self, valor):
        if valor >= 0:
            self.pwm_R_fwd.duty_u16(self._duty(valor))
            self.pwm_R_rev.duty_u16(0)
        else:
            self.pwm_R_fwd.duty_u16(0)
            self.pwm_R_rev.duty_u16(self._duty(-valor))

    def _set_cuchilla(self, valor):
        self.pwm_cuch.duty_u16(self._duty(valor))

    def frenar(self):
        self._set_motor_L(0.0)
        self._set_motor_R(0.0)
        self.pid_L.reset()
        self.pid_R.reset()

    def parada_emergencia(self):
        self.frenar()
        self._set_cuchilla(0.0)
        self.en_cuch.value(0)

    def actualizar(self, rpm_L, rpm_R, vel_target_L, vel_target_R, pwm_cuch_target):
        """Llamar a 200 Hz. Convierte vel (m/s) a RPM y aplica PID."""
        # Convertir m/s a RPM
        factor = 60.0 / (2 * math.pi * RADIO_RUEDA_M)
        rpm_target_L = vel_target_L * factor
        rpm_target_R = vel_target_R * factor

        pwm_L = self.pid_L.calcular(rpm_target_L, rpm_L)
        pwm_R = self.pid_R.calcular(rpm_target_R, rpm_R)

        self._set_motor_L(pwm_L)
        self._set_motor_R(pwm_R)
        self._set_cuchilla(pwm_cuch_target)

        shared_write_multi({'pwm_L_actual': pwm_L, 'pwm_R_actual': pwm_R})


# =============================================================================
#  TAREA 2: LECTURA DE ENCODERS  (core 0, 200 Hz con interrupciones)
# =============================================================================

class LectorEncoders:
    """Encoders cuadraturas con interrupción. Mide RPM en ventanas de 50 ms."""

    def __init__(self):
        self._count_L = 0
        self._count_R = 0
        self._dir_L   = 1
        self._dir_R   = 1
        self._ts_prev = utime.ticks_us()

        self.enc_L_A = Pin(PIN_ENC_L_A, Pin.IN, Pin.PULL_UP)
        self.enc_L_B = Pin(PIN_ENC_L_B, Pin.IN, Pin.PULL_UP)
        self.enc_R_A = Pin(PIN_ENC_R_A, Pin.IN, Pin.PULL_UP)
        self.enc_R_B = Pin(PIN_ENC_R_B, Pin.IN, Pin.PULL_UP)

        self.enc_L_A.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING,
                         handler=self._irq_L)
        self.enc_R_A.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING,
                         handler=self._irq_R)

        self._ventana_L = []
        self._ventana_R = []

    def _irq_L(self, pin):
        self._dir_L = 1 if self.enc_L_B.value() != pin.value() else -1
        self._count_L += self._dir_L

    def _irq_R(self, pin):
        self._dir_R = 1 if self.enc_R_B.value() != pin.value() else -1
        self._count_R += self._dir_R

    def calcular_rpm(self):
        """Llamar cada 50 ms. Devuelve (rpm_L, rpm_R)."""
        ts_ahora = utime.ticks_us()
        dt_s = utime.ticks_diff(ts_ahora, self._ts_prev) / 1_000_000
        self._ts_prev = ts_ahora

        cnt_L = self._count_L
        cnt_R = self._count_R
        self._count_L = 0
        self._count_R = 0

        if dt_s > 0:
            rpm_L = (cnt_L / PULSOS_POR_REV) * (60.0 / dt_s)
            rpm_R = (cnt_R / PULSOS_POR_REV) * (60.0 / dt_s)
        else:
            rpm_L = rpm_R = 0.0

        # Velocidad lineal por rueda
        v_L = (rpm_L / 60.0) * (2 * math.pi * RADIO_RUEDA_M)
        v_R = (rpm_R / 60.0) * (2 * math.pi * RADIO_RUEDA_R)

        return rpm_L, rpm_R, v_L, v_R

    def calcular_slip(self, rpm_real, pwm_aplicado):
        """Slip = desviación entre velocidad esperada y real. 0=sin slip, 1=total."""
        rpm_esperado = abs(pwm_aplicado) * 150.0  # 150 RPM a PWM=1.0 (calibrar)
        if rpm_esperado < 1.0:
            return 0.0
        slip = 1.0 - min(1.0, abs(rpm_real) / rpm_esperado)
        return max(0.0, slip)


# =============================================================================
#  TAREA 3: LECTURA DE SENSORES  (core 0, 100 Hz)
# =============================================================================

class LectorIMU_MPU6050:
    """Driver MPU-6050 por I2C. Lee acelerómetro y giróscopo."""

    REG_PWR_MGMT   = 0x6B
    REG_ACCEL_XOUT = 0x3B
    REG_GYRO_XOUT  = 0x43
    ACCEL_SCALE    = 16384.0   # ±2g
    GYRO_SCALE     = 131.0     # ±250 deg/s

    def __init__(self, i2c, addr=ADDR_IMU_MPU6050):
        self.i2c  = i2c
        self.addr = addr
        # Despertar MPU6050 (por defecto está en sleep)
        self.i2c.writeto_mem(self.addr, self.REG_PWR_MGMT, b'\x00')
        utime.sleep_ms(100)
        self._buf = bytearray(14)
        # Buffer para cálculo de vibración RMS (ventana 50 muestras)
        self._vib_buffer = []
        self._VIB_WINDOW = 50

    def leer(self):
        """Devuelve (ax_ms2, ay_ms2, az_ms2, gz_rads)"""
        self.i2c.readfrom_mem_into(self.addr, self.REG_ACCEL_XOUT, self._buf)

        def s16(hi, lo):
            v = (hi << 8) | lo
            return v - 65536 if v > 32767 else v

        ax_g = s16(self._buf[0], self._buf[1]) / self.ACCEL_SCALE
        ay_g = s16(self._buf[2], self._buf[3]) / self.ACCEL_SCALE
        az_g = s16(self._buf[4], self._buf[5]) / self.ACCEL_SCALE
        gz_d = s16(self._buf[12], self._buf[13]) / self.GYRO_SCALE

        # Convertir a SI
        G = 9.80665
        ax = ax_g * G
        ay = ay_g * G
        az = az_g * G
        gz = math.radians(gz_d)

        # Calcular vibración RMS (magnitud aceleración sin gravedad)
        mag = math.sqrt(ax*ax + ay*ay + az*az) - G
        self._vib_buffer.append(mag * mag)
        if len(self._vib_buffer) > self._VIB_WINDOW:
            self._vib_buffer.pop(0)
        vib_rms = math.sqrt(sum(self._vib_buffer) / len(self._vib_buffer))

        return ax, ay, az, gz, vib_rms


class LectorINA219:
    """Driver INA219 por I2C. Lee corriente y voltaje."""

    REG_CONFIG   = 0x00
    REG_SHUNT    = 0x01
    REG_BUS      = 0x02
    REG_CURRENT  = 0x04
    REG_CALIB    = 0x05

    # Configuración: 32V, 2A, 12-bit, promedio x4
    CONFIG_VAL   = 0x3FFF
    CALIB_VAL    = 4096
    LSB_CURRENT  = 0.0001   # 100 µA por LSB

    def __init__(self, i2c, addr):
        self.i2c  = i2c
        self.addr = addr
        self._write_reg(self.REG_CONFIG, self.CONFIG_VAL)
        self._write_reg(self.REG_CALIB,  self.CALIB_VAL)

    def _write_reg(self, reg, val):
        self.i2c.writeto_mem(self.addr, reg,
                             bytes([(val >> 8) & 0xFF, val & 0xFF]))

    def _read_reg(self, reg):
        data = self.i2c.readfrom_mem(self.addr, reg, 2)
        val = (data[0] << 8) | data[1]
        return val - 65536 if val > 32767 else val

    def leer(self):
        """Devuelve (corriente_A, voltaje_V)"""
        corriente = self._read_reg(self.REG_CURRENT) * self.LSB_CURRENT
        bus_raw   = self._read_reg(self.REG_BUS)
        voltaje   = ((bus_raw >> 3) & 0x1FFF) * 0.004   # 4 mV por LSB
        return abs(corriente), voltaje


class LectorUltrasonido:
    """HC-SR04. Medición de distancia por tiempo de vuelo."""

    def __init__(self):
        self.trig = Pin(PIN_ULTRAS_TRIG, Pin.OUT)
        self.echo = Pin(PIN_ULTRAS_ECHO, Pin.IN)
        self.trig.value(0)
        self._dist_prev = 999.0

    def medir_cm(self):
        """Devuelve distancia en cm. 999 = sin eco (fuera de rango)."""
        self.trig.value(0)
        utime.sleep_us(2)
        self.trig.value(1)
        utime.sleep_us(10)
        self.trig.value(0)

        timeout = utime.ticks_us()
        while self.echo.value() == 0:
            if utime.ticks_diff(utime.ticks_us(), timeout) > 30000:
                return self._dist_prev

        inicio = utime.ticks_us()
        while self.echo.value() == 1:
            if utime.ticks_diff(utime.ticks_us(), inicio) > 30000:
                return self._dist_prev

        duracion_us = utime.ticks_diff(utime.ticks_us(), inicio)
        distancia = duracion_us * 0.0343 / 2
        if 2.0 < distancia < 400.0:
            self._dist_prev = distancia
        return self._dist_prev


# =============================================================================
#  TAREA 5: REGISTRO DE TELEMETRÍA  (core 1, 2 Hz)
# =============================================================================

class Telemetria:
    """Registra datos en archivo CSV en la flash del Pico W."""

    CAMPOS = ['ts', 'modo', 'clase_suelo', 'confianza',
              'i_trac', 'i_cuch', 'volt', 'rpm_L', 'rpm_R',
              'vib_rms', 'slip_L', 'slip_R',
              'pos_x', 'pos_y', 'theta', 'dist_cm',
              'pwm_L', 'pwm_R', 'pwm_cuch', 'anomalia']

    def __init__(self, archivo='telemetria.csv', max_lineas=5000):
        self.archivo    = archivo
        self.max_lineas = max_lineas
        self._lineas    = 0
        self._init_archivo()

    def _init_archivo(self):
        try:
            with open(self.archivo, 'r') as f:
                self._lineas = sum(1 for _ in f) - 1
        except OSError:
            with open(self.archivo, 'w') as f:
                f.write(','.join(self.CAMPOS) + '\n')
            self._lineas = 0

    def registrar(self, datos: dict):
        if self._lineas >= self.max_lineas:
            return  # Flash llena — en producción rotar archivo
        fila = ','.join(str(datos.get(c, '')) for c in self.CAMPOS)
        try:
            with open(self.archivo, 'a') as f:
                f.write(fila + '\n')
            self._lineas += 1
        except OSError:
            pass  # Flash llena


# =============================================================================
#  TAREA 6: CLASIFICADOR DE SUELO  (core 1, 10 Hz)
# =============================================================================

class ClasificadorSuelo:
    """
    Árbol de decisión embebido como reglas if/elif.
    
    Generado desde sklearn.DecisionTreeClassifier entrenado con datos reales.
    Reemplazar los umbrales por los valores del modelo entrenado.
    
    Features de entrada (todas normalizadas en el método predict):
      [0] i_traccion   — corriente motores tracción [A]
      [1] i_cuchilla   — corriente motor cuchilla [A]
      [2] slip          — promedio slip ruedas (0.0–1.0)
      [3] vib_rms       — vibración RMS del IMU [m/s²]
      [4] pwm_ratio     — pwm_promedio / max(rpm_promedio, 1)
    
    Clases de salida:
      0: pasto_corto
      1: pasto_alto
      2: suelo_blando
      3: tierra_firme
      4: superficie_dura
    """

    CLASES = ['pasto_corto', 'pasto_alto', 'suelo_blando',
              'tierra_firme', 'superficie_dura']

    # Acciones por clase: [mult_vel, pwm_cuchilla, sep_tray_cm, desc]
    ACCIONES = {
        'pasto_corto':    {'vel': 1.0,  'cuch': 0.80, 'sep': 20.0,
                           'desc': 'velocidad normal, corte estandar'},
        'pasto_alto':     {'vel': 0.55, 'cuch': 1.00, 'sep': 15.0,
                           'desc': 'lento, cuchilla maxima'},
        'suelo_blando':   {'vel': 0.35, 'cuch': 0.50, 'sep': 25.0,
                           'desc': 'muy lento, evitar hundimiento'},
        'tierra_firme':   {'vel': 0.90, 'cuch': 0.70, 'sep': 20.0,
                           'desc': 'normal, sin ajuste'},
        'superficie_dura':{'vel': 0.80, 'cuch': 0.00, 'sep': 30.0,
                           'desc': 'cuchilla apagada, pasar rapido'},
    }

    # Umbrales del árbol de decisión entrenado
    # IMPORTANTE: estos son valores de ejemplo. Reemplazar con los del modelo
    # real ejecutando: python3 entrenamiento/exportar_modelo.py
    UMBRALES = {
        'i_trac_alto':    3.5,    # A — tracción alta indica suelo resistente
        'i_trac_medio':   2.0,
        'i_cuch_alto':    2.5,    # A — cuchilla alta indica vegetación densa
        'i_cuch_medio':   1.2,
        'slip_alto':      0.25,   # slip alto indica suelo blando/resbaladizo
        'slip_medio':     0.10,
        'vib_alta':       3.5,    # m/s² — vibración alta indica terreno irregular
        'vib_media':      1.8,
        'pwm_ratio_alto': 1.4,    # pwm alto con poco movimiento
    }

    def __init__(self):
        self._historial = []       # suavizado temporal (últimas 5 clasificaciones)
        self._HIST_LEN  = 5
        self._cargar_modelo_flash()

    def _cargar_modelo_flash(self):
        """Intenta cargar umbrales calibrados desde flash."""
        try:
            with open('model_umbrales.json', 'r') as f:
                umbrales_cargados = json.load(f)
                self.UMBRALES.update(umbrales_cargados)
        except OSError:
            pass  # Usar umbrales por defecto

    def _arbol_decision(self, it, ic, slip, vib, pwm_ratio):
        """
        Árbol de decisión como código Python.
        
        Estructura basada en análisis de las señales físicas del terreno.
        Los umbrales vienen de UMBRALES y son reemplazables al entrenar.
        """
        U = self.UMBRALES

        # Nodo raíz: ¿hay corriente de tracción alta?
        if it > U['i_trac_alto']:
            # Suelo que ofrece resistencia al movimiento
            if slip > U['slip_alto']:
                return 2, 0.90  # suelo_blando — alta tracción + slip
            elif vib > U['vib_alta']:
                return 3, 0.80  # tierra_firme irregular
            else:
                return 3, 0.75  # tierra_firme

        elif it > U['i_trac_medio']:
            # Tracción media
            if ic > U['i_cuch_alto']:
                if vib > U['vib_media']:
                    return 1, 0.85  # pasto_alto con terreno irregular
                else:
                    return 1, 0.90  # pasto_alto limpio
            elif slip > U['slip_medio']:
                return 2, 0.70  # posible suelo blando moderado
            else:
                return 0, 0.80  # pasto_corto

        else:
            # Tracción baja
            if ic < 0.5 and vib < 1.0:
                return 4, 0.92  # superficie_dura — sin resistencia
            elif ic > U['i_cuch_medio']:
                return 1, 0.75  # pasto_alto con poca resistencia de tracción
            elif pwm_ratio > U['pwm_ratio_alto']:
                return 2, 0.65  # posible barro — ruedas giran sin avanzar
            else:
                return 0, 0.85  # pasto_corto normal

    def predict(self, i_traccion, i_cuchilla, slip, vib_rms, pwm_ratio):
        """
        Clasifica el suelo con suavizado temporal.
        
        Devuelve: (clase_str, confianza_float, accion_dict)
        """
        idx, conf = self._arbol_decision(i_traccion, i_cuchilla,
                                          slip, vib_rms, pwm_ratio)

        # Suavizado: voto mayoritario sobre historial
        self._historial.append(idx)
        if len(self._historial) > self._HIST_LEN:
            self._historial.pop(0)

        # Conteo de votos
        conteo = [0] * len(self.CLASES)
        for v in self._historial:
            conteo[v] += 1
        idx_suavizado = conteo.index(max(conteo))

        clase   = self.CLASES[idx_suavizado]
        accion  = self.ACCIONES[clase]
        return clase, conf, accion


# =============================================================================
#  DETECTOR DE ANOMALÍAS
# =============================================================================

class DetectorAnomalias:
    """
    Detecta fallas en tiempo real a partir de las señales de sensores.
    Reglas basadas en la sección 16 del documento de diseño.
    """

    def __init__(self):
        self._cnt_bloqueo_cuch  = 0
        self._cnt_rueda_bloq    = 0
        self._cnt_bateria_baja  = 0

    def analizar(self, s: dict):
        """
        s: snapshot del buffer compartido.
        Devuelve: (anomalia_str | None, accion_str)
        """
        anomalia = None
        accion   = 'continuar'

        # Regla 1: bloqueo de cuchilla
        # corriente alta + RPM cuchilla baja (si tenés encoder en cuchilla)
        if s['i_cuchilla'] > LIMITE_CORRIENTE_CUCH_A * 0.85:
            self._cnt_bloqueo_cuch += 1
            if self._cnt_bloqueo_cuch > 5:
                anomalia = 'BLOQUEO_CUCHILLA'
                accion   = 'apagar_cuchilla'
        else:
            self._cnt_bloqueo_cuch = max(0, self._cnt_bloqueo_cuch - 1)

        # Regla 2: rueda bloqueada
        # PWM alto pero encoder no cambia
        if abs(s['pwm_L_actual']) > 0.5 and abs(s['rpm_L']) < 5:
            self._cnt_rueda_bloq += 1
            if self._cnt_rueda_bloq > 10:
                anomalia = 'RUEDA_IZQUIERDA_BLOQUEADA'
                accion   = 'retroceder_y_girar'
        elif abs(s['pwm_R_actual']) > 0.5 and abs(s['rpm_R']) < 5:
            self._cnt_rueda_bloq += 1
            if self._cnt_rueda_bloq > 10:
                anomalia = 'RUEDA_DERECHA_BLOQUEADA'
                accion   = 'retroceder_y_girar'
        else:
            self._cnt_rueda_bloq = max(0, self._cnt_rueda_bloq - 1)

        # Regla 3: batería baja
        if s['voltaje'] < VOLTAJE_BATERIA_MIN_V:
            self._cnt_bateria_baja += 1
            if self._cnt_bateria_baja > 3:
                anomalia = 'BATERIA_CRITICA'
                accion   = 'detener_todo'
        else:
            self._cnt_bateria_baja = max(0, self._cnt_bateria_baja - 1)

        # Regla 4: sobrecorriente tracción
        if s['i_traccion'] > LIMITE_CORRIENTE_TRAC_A:
            anomalia = 'SOBRECORRIENTE_TRACCION'
            accion   = 'frenar_inmediato'

        return anomalia, accion


# =============================================================================
#  TAREA 4: NAVEGACIÓN AUTÓNOMA  (core 1, 20 Hz)
# =============================================================================

class Navegacion:
    """
    Algoritmo de cobertura adaptativa.
    Adapta velocidad y separación de trayectorias según la clase de suelo.
    """

    DIST_OBSTACULO_CM   = 30.0   # umbral detección obstacle
    VEL_BASE_MS         = 0.25   # m/s en condiciones normales
    VEL_RETROCESO_MS    = 0.15
    ANGULO_GIRO_RAD     = math.pi / 2   # 90° para patrón cuadrícula

    def __init__(self):
        self.estado          = 'AVANZANDO'
        self._ts_maniobra    = 0
        self._angulo_actual  = 0.0   # radianes
        self._pasadas        = 0
        self._sep_actual_m   = 0.20  # separación actual entre pasadas

    def calcular_velocidades(self, dist_cm, clase_suelo, accion_vel,
                             sep_cm, anomalia):
        """
        Máquina de estados de navegación.
        Devuelve (vel_target_L, vel_target_R) en m/s.
        """

        # --- Parada de emergencia ---
        if anomalia in ('BATERIA_CRITICA', 'SOBRECORRIENTE_TRACCION',
                        'BLOQUEO_CUCHILLA'):
            self.estado = 'EMERGENCIA'

        if self.estado == 'EMERGENCIA':
            return 0.0, 0.0

        # Adaptar separación desde IA
        self._sep_actual_m = sep_cm / 100.0

        # Velocidad base adaptada por clase de suelo
        vel = self.VEL_BASE_MS * accion_vel

        ts_ahora = utime.ticks_ms()

        if self.estado == 'AVANZANDO':
            if dist_cm < self.DIST_OBSTACULO_CM:
                self.estado = 'RETROCEDIENDO'
                self._ts_maniobra = ts_ahora
            else:
                return vel, vel

        elif self.estado == 'RETROCEDIENDO':
            elapsed = utime.ticks_diff(ts_ahora, self._ts_maniobra)
            if elapsed < 600:   # retroceder 600 ms
                return -self.VEL_RETROCESO_MS, -self.VEL_RETROCESO_MS
            else:
                self.estado = 'GIRANDO'
                self._ts_maniobra = ts_ahora
                self._pasadas += 1

        elif self.estado == 'GIRANDO':
            elapsed = utime.ticks_diff(ts_ahora, self._ts_maniobra)
            # Tiempo de giro ≈ (ángulo * distancia_ejes) / (2 * vel_giro)
            t_giro_ms = int((self.ANGULO_GIRO_RAD * DISTANCIA_EJES_M
                             / (2 * self.VEL_RETROCESO_MS)) * 1000)
            if elapsed < t_giro_ms:
                # Girar en su lugar (sentido alternado por pasada)
                if self._pasadas % 2 == 0:
                    return -self.VEL_RETROCESO_MS, self.VEL_RETROCESO_MS
                else:
                    return self.VEL_RETROCESO_MS, -self.VEL_RETROCESO_MS
            else:
                self.estado = 'AVANZANDO'

        return vel, vel


# =============================================================================
#  ODOMETRÍA
# =============================================================================

class Odometria:
    """Calcula posición (x, y, θ) a partir de encoders."""

    def __init__(self):
        self.x     = 0.0
        self.y     = 0.0
        self.theta = 0.0

    def actualizar(self, v_L, v_R, dt):
        """Modelo diferencial de tracción."""
        v = (v_L + v_R) / 2.0
        omega = (v_R - v_L) / DISTANCIA_EJES_M

        self.x     += v * math.cos(self.theta) * dt
        self.y     += v * math.sin(self.theta) * dt
        self.theta += omega * dt
        # Normalizar ángulo a [-π, π]
        self.theta  = math.atan2(math.sin(self.theta),
                                  math.cos(self.theta))


# =============================================================================
#  LOOP CORE 0 — Tiempo real
# =============================================================================

def _loop_core0():
    """Core 0: encoders, sensores, control motores. Ciclo 5 ms (200 Hz)."""

    i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=I2C_FREQ)

    motores  = ControlMotores()
    encoders = LectorEncoders()
    imu      = LectorIMU_MPU6050(i2c)
    ina_trac = LectorINA219(i2c, ADDR_INA219_TRAC)
    ina_cuch = LectorINA219(i2c, ADDR_INA219_CUCH)
    ultrason = LectorUltrasonido()
    odometria= Odometria()

    estop    = Pin(PIN_ESTOP,     Pin.IN, Pin.PULL_UP)
    elevado  = Pin(PIN_ELEVACION, Pin.IN, Pin.PULL_UP)

    CICLO_US    = 5_000    # 5 ms = 200 Hz
    cnt_sensor  = 0        # divisor para sensores lentos

    t_prev = utime.ticks_us()

    while True:
        t_ini = utime.ticks_us()

        # --- Seguridad (cada ciclo, sin excepciones) ---
        is_estop   = (estop.value() == 0)
        is_elevado = (elevado.value() == 0)

        if is_estop or is_elevado:
            motores.parada_emergencia()
            shared_write_multi({'estop': is_estop, 'elevado': is_elevado,
                                'modo': 'EMERGENCIA'})
            utime.sleep_ms(50)
            continue

        # --- Encoders (cada ciclo: 200 Hz) ---
        rpm_L, rpm_R, v_L, v_R = encoders.calcular_rpm()

        # --- Odometría ---
        dt = utime.ticks_diff(t_ini, t_prev) / 1_000_000
        t_prev = t_ini
        odometria.actualizar(v_L, v_R, dt)

        # --- Sensores lentos (cada 2 ciclos: 100 Hz IMU, cada 20: 10 Hz INA) ---
        cnt_sensor += 1
        if cnt_sensor % 2 == 0:
            ax, ay, az, gz, vib_rms = imu.leer()
            shared_write_multi({
                'accel_x': ax, 'accel_y': ay, 'accel_z': az,
                'giro_z': gz, 'vib_rms': vib_rms
            })

        if cnt_sensor % 20 == 0:
            i_trac, v_bat = ina_trac.leer()
            i_cuch, _     = ina_cuch.leer()
            dist_cm       = ultrason.medir_cm()
            shared_write_multi({
                'i_traccion': i_trac, 'i_cuchilla': i_cuch,
                'voltaje': v_bat, 'distancia_cm': dist_cm
            })

        if cnt_sensor >= 200:
            cnt_sensor = 0

        # --- Leer setpoints del core 1 ---
        sp = shared_read_multi(['vel_target_L', 'vel_target_R',
                                 'pwm_cuchilla', 'modo'])

        # --- Actualizar motores ---
        if sp['modo'] == 'EMERGENCIA':
            motores.parada_emergencia()
        else:
            motores.actualizar(rpm_L, rpm_R,
                               sp['vel_target_L'], sp['vel_target_R'],
                               sp['pwm_cuchilla'])

        # --- Actualizar buffer ---
        shared_write_multi({
            'rpm_L': rpm_L, 'rpm_R': rpm_R,
            'pos_x': odometria.x, 'pos_y': odometria.y,
            'theta': odometria.theta, 'ts': utime.ticks_ms()
        })

        # --- Mantener ciclo exacto de 200 Hz ---
        elapsed = utime.ticks_diff(utime.ticks_us(), t_ini)
        restante = CICLO_US - elapsed
        if restante > 0:
            utime.sleep_us(restante)


# =============================================================================
#  LOOP CORE 1 — Alto nivel
# =============================================================================

def _loop_core1():
    """Core 1: clasificador IA, navegación, telemetría."""
    utime.sleep_ms(200)  # Esperar que core 0 inicialice

    clasificador = ClasificadorSuelo()
    navegacion   = Navegacion()
    telemetria   = Telemetria()
    detector     = DetectorAnomalias()

    CICLO_NAV_MS   = 50    # 20 Hz
    CICLO_CLAS_MS  = 100   # 10 Hz
    CICLO_TEL_MS   = 500   # 2 Hz

    t_nav  = utime.ticks_ms()
    t_clas = utime.ticks_ms()
    t_tel  = utime.ticks_ms()

    while True:
        ts = utime.ticks_ms()

        # --- Tarea 6: Clasificador de suelo (10 Hz) ---
        if utime.ticks_diff(ts, t_clas) >= CICLO_CLAS_MS:
            t_clas = ts

            s = shared_read_multi(['i_traccion', 'i_cuchilla', 'rpm_L',
                                    'rpm_R', 'pwm_L_actual', 'pwm_R_actual',
                                    'vib_rms'])

            # Calcular slip promedio
            slip_L = _calc_slip(s['rpm_L'], s['pwm_L_actual'])
            slip_R = _calc_slip(s['rpm_R'], s['pwm_R_actual'])
            slip   = (slip_L + slip_R) / 2.0

            # Ratio PWM/velocidad (indicador de eficiencia de tracción)
            rpm_prom = (abs(s['rpm_L']) + abs(s['rpm_R'])) / 2.0
            pwm_prom = (abs(s['pwm_L_actual']) + abs(s['pwm_R_actual'])) / 2.0
            pwm_ratio = pwm_prom / max(rpm_prom / 150.0, 0.01)

            clase, conf, accion = clasificador.predict(
                s['i_traccion'], s['i_cuchilla'],
                slip, s['vib_rms'], pwm_ratio
            )

            shared_write_multi({
                'clase_suelo':     clase,
                'confianza_suelo': conf,
                'accion_vel':      accion['vel'],
                'accion_sep_cm':   accion['sep'],
                'pwm_cuchilla':    accion['cuch'],
            })

        # --- Detección de anomalías (cada ciclo de navegación) ---
        if utime.ticks_diff(ts, t_nav) >= CICLO_NAV_MS:
            t_nav = ts

            s = shared_read_multi(['i_traccion', 'i_cuchilla', 'voltaje',
                                    'rpm_L', 'rpm_R', 'pwm_L_actual',
                                    'pwm_R_actual', 'distancia_cm',
                                    'clase_suelo', 'accion_vel',
                                    'accion_sep_cm', 'modo'])

            anomalia, accion_anom = detector.analizar(s)
            if anomalia:
                shared_write('anomalia', anomalia)
                if accion_anom == 'detener_todo':
                    shared_write('modo', 'EMERGENCIA')

            # --- Tarea 4: Navegación (20 Hz) ---
            vL, vR = navegacion.calcular_velocidades(
                dist_cm    = s['distancia_cm'],
                clase_suelo= s['clase_suelo'],
                accion_vel = s['accion_vel'],
                sep_cm     = s['accion_sep_cm'],
                anomalia   = anomalia
            )
            shared_write_multi({'vel_target_L': vL, 'vel_target_R': vR})

        # --- Tarea 5: Telemetría (2 Hz) ---
        if utime.ticks_diff(ts, t_tel) >= CICLO_TEL_MS:
            t_tel = ts
            snap = shared_read_multi([
                'ts', 'modo', 'clase_suelo', 'confianza_suelo',
                'i_traccion', 'i_cuchilla', 'voltaje',
                'rpm_L', 'rpm_R', 'vib_rms',
                'pos_x', 'pos_y', 'theta', 'distancia_cm',
                'pwm_L_actual', 'pwm_R_actual', 'pwm_cuchilla', 'anomalia'
            ])
            # Adaptar claves al CSV
            fila = {
                'ts':         snap['ts'],
                'modo':       snap['modo'],
                'clase_suelo':snap['clase_suelo'],
                'confianza':  round(snap['confianza_suelo'], 3),
                'i_trac':     round(snap['i_traccion'], 3),
                'i_cuch':     round(snap['i_cuchilla'], 3),
                'volt':       round(snap['voltaje'], 2),
                'rpm_L':      round(snap['rpm_L'], 1),
                'rpm_R':      round(snap['rpm_R'], 1),
                'vib_rms':    round(snap['vib_rms'], 3),
                'slip_L':     round(_calc_slip(snap['rpm_L'], snap['pwm_L_actual']), 3),
                'slip_R':     round(_calc_slip(snap['rpm_R'], snap['pwm_R_actual']), 3),
                'pos_x':      round(snap['pos_x'], 4),
                'pos_y':      round(snap['pos_y'], 4),
                'theta':      round(snap['theta'], 4),
                'dist_cm':    round(snap['distancia_cm'], 1),
                'pwm_L':      round(snap['pwm_L_actual'], 3),
                'pwm_R':      round(snap['pwm_R_actual'], 3),
                'pwm_cuch':   round(snap['pwm_cuchilla'], 3),
                'anomalia':   snap['anomalia'] or '',
            }
            telemetria.registrar(fila)

        utime.sleep_ms(5)


def _calc_slip(rpm_real, pwm):
    rpm_esp = abs(pwm) * 150.0
    if rpm_esp < 1.0:
        return 0.0
    return max(0.0, 1.0 - min(1.0, abs(rpm_real) / rpm_esp))


# =============================================================================
#  PUNTO DE ENTRADA
# =============================================================================

def main():
    print("[BOOT] Robot autonomo de corte v2.0")
    print("[BOOT] Iniciando core 1...")
    _thread.start_new_thread(_loop_core1, ())
    print("[BOOT] Iniciando core 0 (tiempo real)...")
    _loop_core0()   # Core 0 corre en el hilo principal


if __name__ == '__main__':
    main()
