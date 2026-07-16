"""
fact_servicios.py - VERSIÓN FINAL DEFINITIVA
Fix 1: Chunksize reducido (500 filas) sin method='multi' para evitar error 9h9h.
Fix 2: Parsing robusto de hora_solicitud (maneja objetos time de PostgreSQL).
Fix 3: NUMERIC(15,2) para evitar desbordamiento en cálculos de tiempo.
Fix 4: Manejo correcto de 'descripcion_cancelado' y estado "Cancelado".
"""
import sys
import os
# Agregar la carpeta padre al path para poder importar utils desde cualquier lugar
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from sqlalchemy.engine import Engine
from sqlalchemy import text
from datetime import time as dt_time
from utils import MOTOR_ORIGEN, MOTOR_BODEGA, get_logger

logger = get_logger(__name__)


# ============================================================
# 1. EXTRACT
# ============================================================
SQL_SERVICIOS = """
    SELECT
        s.id AS id_servicio,
        s.descripcion,
        s.fecha_solicitud,
        s.hora_solicitud,
        s.fecha_deseada,
        s.hora_deseada,
        s.cliente_id,
        s.mensajero_id,
        s.origen_id,
        s.destino_id,
        s.ciudad_origen_id,
        s.ciudad_destino_id,
        s.tipo_servicio_id,
        s.tipo_vehiculo_id,
        s.prioridad,
        s.es_prueba
    FROM public.mensajeria_servicio s
    WHERE s.es_prueba = FALSE;
"""

SQL_ESTADOS_SERVICIO = """
    SELECT
        es.servicio_id,
        es.fecha,
        es.hora,
        e.nombre AS estado_nombre
    FROM public.mensajeria_estadosservicio es
    INNER JOIN public.mensajeria_estado e ON e.id = es.estado_id
    WHERE es.es_prueba = FALSE;
"""

SQL_NOVEDADES = """
    SELECT
        n.servicio_id,
        n.tipo_novedad_id,
        n.fecha_novedad
    FROM public.mensajeria_novedadesservicio n
    WHERE n.es_prueba = FALSE;
"""

SQL_SEDES = """
    SELECT sede_id, cliente_id, ciudad_id
    FROM public.sede;
"""


def extraer(motor: Engine = None) -> dict:
    logger.info("Extrayendo datos para FACT_SERVICIOS...")
    motor = motor or MOTOR_ORIGEN
    datos = {
        "servicios": pd.read_sql(SQL_SERVICIOS, motor),
        "estados_servicio": pd.read_sql(SQL_ESTADOS_SERVICIO, motor),
        "novedades": pd.read_sql(SQL_NOVEDADES, motor),
        "sedes": pd.read_sql(SQL_SEDES, motor),
    }
    for k, v in datos.items():
        logger.info(f"  -> {len(v)} filas de {k}")
    if not datos["estados_servicio"].empty:
        logger.info(f"  -> Estados únicos: {datos['estados_servicio']['estado_nombre'].unique().tolist()}")
    return datos


# ============================================================
# 2. TRANSFORM
# ============================================================
def _construir_mapeos_sk(motor_bodega: Engine) -> dict:
    logger.info("Construyendo mapeos de SK...")

    def leer(tabla, col_ops, col_sk):
        df = pd.read_sql(f"SELECT {col_ops}, {col_sk} FROM {tabla}", motor_bodega)
        return dict(zip(df[col_ops].astype(int), df[col_sk].astype(int)))

    mapeos = {
        "cliente": leer("dim_cliente", "id_cliente_ops", "id_cliente"),
        "sede": leer("dim_sede", "id_sede_ops", "id_sede"),
        "mensajero": leer("dim_mensajero", "id_mensajero_ops", "id_mensajero"),
        "ciudad": leer("dim_ciudad", "id_ciudad_ops", "id_ciudad"),
        "tipo_entrega": leer("dim_tipo_entrega", "id_tipo_entrega_ops", "id_tipo_entrega"),
        "tipo_vehiculo": leer("dim_tipo_vehiculo", "id_tipo_vehiculo_ops", "id_tipo_vehiculo"),
        "novedad": leer("dim_novedad", "id_novedad_ops", "id_novedad"),
    }
    df_t = pd.read_sql("SELECT fecha_completa, id_tiempo FROM dim_tiempo WHERE id_tiempo > 0", motor_bodega)
    mapeos["tiempo"] = dict(zip(df_t["fecha_completa"], df_t["id_tiempo"]))
    logger.info(f"  -> {len(mapeos['tiempo'])} fechas mapeadas")
    return mapeos


def _extraer_hora(valor) -> int:
    """Función robusta para extraer la hora de un valor time, timedelta, string o datetime."""
    if pd.isna(valor) or valor is None:
        return 0
    if isinstance(valor, dt_time):
        return valor.hour
    if hasattr(valor, 'hour'):
        return int(valor.hour)
    if isinstance(valor, str):
        try:
            return int(valor.split(':')[0])
        except (ValueError, IndexError):
            return 0
    if hasattr(valor, 'total_seconds'):
        total_seg = valor.total_seconds()
        if total_seg < 86400:
            return int(total_seg // 3600) % 24
    return 0


def transformar(datos: dict, mapeos: dict) -> pd.DataFrame:
    logger.info("Transformando FACT_SERVICIOS...")

    servicios = datos["servicios"].copy()
    estados = datos["estados_servicio"].copy()
    novedades = datos["novedades"].copy()
    sedes = datos["sedes"].copy()

    # --- PIVOT DE ESTADOS ---
    estados["timestamp"] = pd.to_datetime(
        estados["fecha"].astype(str) + " " + estados["hora"].astype(str),
        errors="coerce"
    )

    pivot = estados.pivot_table(
        index="servicio_id",
        columns="estado_nombre",
        values="timestamp",
        aggfunc="first"
    ).reset_index()

    mapping = {
        "Iniciado": "ts_iniciado",
        "Con mensajero Asignado": "ts_asignado",
        "Recogido por mensajero": "ts_recogido",
        "Entregado en destino": "ts_entregado",
        "Terminado completo": "ts_cerrado",
    }
    pivot = pivot.rename(columns={k: v for k, v in mapping.items() if k in pivot.columns})
    for col in ["ts_iniciado", "ts_asignado", "ts_recogido", "ts_entregado", "ts_cerrado"]:
        if col not in pivot.columns:
            pivot[col] = pd.NaT

    # --- MERGE (SIN SUFIJOS EXTRAÑOS) ---
    pivot_clean = pivot.rename(columns={"servicio_id": "id_servicio"})
    fact = servicios.merge(pivot_clean, on="id_servicio", how="left")

    # --- CÁLCULO DE MINUTOS ENTRE FASES ---
    def minutos_entre(col_a, col_b):
        a = pd.to_datetime(fact[col_a], errors="coerce")
        b = pd.to_datetime(fact[col_b], errors="coerce")
        return (b - a).dt.total_seconds().div(60).round(2)

    fact["min_iniciado_a_asignado"] = np.where(
        fact["ts_iniciado"].notna() & fact["ts_asignado"].notna(),
        minutos_entre("ts_iniciado", "ts_asignado"), np.nan)
    fact["min_asignado_a_recogido"] = np.where(
        fact["ts_asignado"].notna() & fact["ts_recogido"].notna(),
        minutos_entre("ts_asignado", "ts_recogido"), np.nan)
    fact["min_recogido_a_entregado"] = np.where(
        fact["ts_recogido"].notna() & fact["ts_entregado"].notna(),
        minutos_entre("ts_recogido", "ts_entregado"), np.nan)
    fact["min_entregado_a_cerrado"] = np.where(
        fact["ts_entregado"].notna() & fact["ts_cerrado"].notna(),
        minutos_entre("ts_entregado", "ts_cerrado"), np.nan)
    fact["min_total_servicio"] = np.where(
        fact["ts_iniciado"].notna() & fact["ts_cerrado"].notna(),
        minutos_entre("ts_iniciado", "ts_cerrado"), np.nan)

    # --- RETRASO VS DESEADO ---
    fact["timestamp_deseado"] = pd.to_datetime(
        fact["fecha_deseada"].astype(str) + " " +
        fact["hora_deseada"].apply(lambda h: h.strftime("%H:%M:%S") if isinstance(h, dt_time) else str(h) if pd.notna(h) else "00:00:00"),
        errors="coerce"
    )
    fact["min_retraso_vs_deseado"] = np.where(
        fact["timestamp_deseado"].notna() & fact["ts_cerrado"].notna(),
        (pd.to_datetime(fact["ts_cerrado"]) - fact["timestamp_deseado"])
            .dt.total_seconds().div(60).round(2),
        np.nan)
    fact["entrega_puntual"] = np.where(
        fact["min_retraso_vs_deseado"].notna(),
        fact["min_retraso_vs_deseado"] <= 0,
        False)

    # --- NOVEDADES ---
    if not novedades.empty:
        primera_nov = (novedades.sort_values("fecha_novedad")
            .groupby("servicio_id")["tipo_novedad_id"].first().reset_index()
            .rename(columns={"servicio_id": "id_servicio", "tipo_novedad_id": "id_novedad_ops"}))
        fact = fact.merge(primera_nov, on="id_servicio", how="left")
        fact["tiene_novedad"] = fact["id_novedad_ops"].notna()
    else:
        fact["id_novedad_ops"] = np.nan
        fact["tiene_novedad"] = False

    # --- ESTADO FINAL (CON SOPORTE PARA CANCELADOS) ---
    def estado_final(row):
        desc_cancelado = row.get("descripcion_cancelado")
        if pd.notna(desc_cancelado) and str(desc_cancelado).strip() and str(desc_cancelado).strip().lower() != "nan":
            return "Cancelado"
        if pd.notna(row.get("ts_cerrado")):
            return "Completado"
        for col in ["ts_entregado", "ts_recogido", "ts_asignado", "ts_iniciado"]:
            if pd.notna(row.get(col)):
                return col.replace("ts_", "").capitalize()
        return "Desconocido"

    fact["estado_final"] = fact.apply(estado_final, axis=1)
    fact["servicio_completado_exitosamente"] = fact["estado_final"] == "Completado"

    # --- EXTRAER HORAS CORRECTAMENTE ---
    logger.info("  -> Extrayendo horas con función robusta...")
    fact["hora_solicitud"] = fact["hora_solicitud"].apply(_extraer_hora)
    fact["hora_deseada"] = fact["hora_deseada"].apply(_extraer_hora)
    logger.info(f"  -> Distribución hora_solicitud (primeras 5): {sorted(fact['hora_solicitud'].unique())[:5]}")

    # --- SURROGATE KEYS ---
    fact["fecha_solicitud_dt"] = pd.to_datetime(fact["fecha_solicitud"], errors="coerce")
    fact["fecha_deseada_dt"] = pd.to_datetime(fact["fecha_deseada"], errors="coerce")

    def mapear(valor, mapeo, default=0):
        if pd.isna(valor): return default
        try: return mapeo.get(int(valor), default)
        except: return default

    fact["id_tiempo_solicitud"] = fact["fecha_solicitud_dt"].dt.date.apply(
        lambda d: mapeos["tiempo"].get(d, 0) if pd.notna(d) else 0)
    fact["id_tiempo_cierre"] = fact["ts_cerrado"].dt.date.apply(
        lambda d: mapeos["tiempo"].get(d, 0) if pd.notna(d) else 0)
    fact["id_tiempo_deseado"] = fact["fecha_deseada_dt"].dt.date.apply(
        lambda d: mapeos["tiempo"].get(d, 0) if pd.notna(d) else 0)
    fact["id_cliente"] = fact["cliente_id"].apply(lambda x: mapear(x, mapeos["cliente"]))
    fact["id_mensajero"] = fact["mensajero_id"].apply(lambda x: mapear(x, mapeos["mensajero"]))
    fact["id_ciudad_origen"] = fact["ciudad_origen_id"].apply(lambda x: mapear(x, mapeos["ciudad"]))
    fact["id_ciudad_destino"] = fact["ciudad_destino_id"].apply(lambda x: mapear(x, mapeos["ciudad"]))
    fact["id_tipo_entrega"] = fact["tipo_servicio_id"].apply(lambda x: mapear(x, mapeos["tipo_entrega"]))
    fact["id_tipo_vehiculo"] = fact["tipo_vehiculo_id"].apply(lambda x: mapear(x, mapeos["tipo_vehiculo"]))
    fact["id_novedad"] = fact["id_novedad_ops"].apply(lambda x: mapear(x, mapeos["novedad"]))

    # --- MAPEO DE SEDES ---
    sedes["key"] = sedes["cliente_id"].astype(str) + "_" + sedes["ciudad_id"].astype(str)
    mapeo_sedes = dict(zip(sedes["key"], sedes["sede_id"]))
    fact["key_origen"] = fact["cliente_id"].astype(str) + "_" + fact["ciudad_origen_id"].astype(str)
    fact["key_destino"] = fact["cliente_id"].astype(str) + "_" + fact["ciudad_destino_id"].astype(str)
    fact["id_sede_origen"] = fact["key_origen"].map(lambda k: mapeo_sedes.get(k, 0))
    fact["id_sede_destino"] = fact["key_destino"].map(lambda k: mapeo_sedes.get(k, 0))

    # --- LIMPIEZA DE STRINGS ---
    fact["prioridad"] = fact["prioridad"].fillna("N/A").astype(str).str[:50]
    fact["descripcion_servicio"] = (fact["descripcion"]
        .fillna("N/A").astype(str)
        .str.replace('\x00', '', regex=False)
        .str[:700])
    fact["estado_final"] = fact["estado_final"].fillna("Desconocido").astype(str).str[:50]

    # --- COLUMNAS FINALES ---
    columnas_fact = [
        "id_servicio",
        "id_tiempo_solicitud", "id_tiempo_cierre", "id_tiempo_deseado",
        "id_cliente", "id_sede_origen", "id_sede_destino", "id_mensajero",
        "id_ciudad_origen", "id_ciudad_destino",
        "id_tipo_entrega", "id_tipo_vehiculo", "id_novedad",
        "hora_solicitud", "hora_deseada",
        "prioridad", "descripcion_servicio", "estado_final",
        "min_iniciado_a_asignado", "min_asignado_a_recogido",
        "min_recogido_a_entregado", "min_entregado_a_cerrado",
        "min_total_servicio", "min_retraso_vs_deseado",
        "tiene_novedad", "servicio_completado_exitosamente", "entrega_puntual",
    ]

    faltantes = [c for c in columnas_fact if c not in fact.columns]
    if faltantes:
        raise KeyError(f"Columnas faltantes: {faltantes}")

    fact_final = fact[columnas_fact].copy()
    fact_final = fact_final.rename(columns={"id_servicio": "id_hecho"})
    fact_final.insert(0, "sk_hecho", range(1, len(fact_final) + 1))

    # --- CONVERSIÓN DE TIPOS ---
    int_cols = ["sk_hecho", "id_hecho", "id_tiempo_solicitud", "id_tiempo_cierre",
                "id_tiempo_deseado", "id_cliente", "id_sede_origen", "id_sede_destino",
                "id_mensajero", "id_ciudad_origen", "id_ciudad_destino",
                "id_tipo_entrega", "id_tipo_vehiculo", "id_novedad",
                "hora_solicitud", "hora_deseada"]
    for col in int_cols:
        fact_final[col] = pd.to_numeric(fact_final[col], errors="coerce").fillna(0).astype(int)
    
    num_cols = ["min_iniciado_a_asignado", "min_asignado_a_recogido",
                "min_recogido_a_entregado", "min_entregado_a_cerrado",
                "min_total_servicio", "min_retraso_vs_deseado"]
    for col in num_cols:
        fact_final[col] = pd.to_numeric(fact_final[col], errors="coerce")
    
    bool_cols = ["tiene_novedad", "servicio_completado_exitosamente", "entrega_puntual"]
    for col in bool_cols:
        fact_final[col] = fact_final[col].fillna(False).astype(bool)

    logger.info(f"  -> {len(fact_final)} filas transformadas")
    return fact_final


# ============================================================
# 3. LOAD
# ============================================================
DDL_FACT_SERVICIOS = """
DROP TABLE IF EXISTS fact_servicios CASCADE;
CREATE TABLE fact_servicios (
    sk_hecho INTEGER PRIMARY KEY,
    id_hecho INTEGER,
    id_tiempo_solicitud INTEGER,
    id_tiempo_cierre INTEGER,
    id_tiempo_deseado INTEGER,
    id_cliente INTEGER,
    id_sede_origen INTEGER,
    id_sede_destino INTEGER,
    id_mensajero INTEGER,
    id_ciudad_origen INTEGER,
    id_ciudad_destino INTEGER,
    id_tipo_entrega INTEGER,
    id_tipo_vehiculo INTEGER,
    id_novedad INTEGER,
    hora_solicitud INTEGER,
    hora_deseada INTEGER,
    prioridad VARCHAR(50),
    descripcion_servicio VARCHAR(700),
    estado_final VARCHAR(50),
    min_iniciado_a_asignado NUMERIC(15,2),
    min_asignado_a_recogido NUMERIC(15,2),
    min_recogido_a_entregado NUMERIC(15,2),
    min_entregado_a_cerrado NUMERIC(15,2),
    min_total_servicio NUMERIC(15,2),
    min_retraso_vs_deseado NUMERIC(15,2),
    tiene_novedad BOOLEAN,
    servicio_completado_exitosamente BOOLEAN,
    entrega_puntual BOOLEAN
);
"""


def cargar(df: pd.DataFrame, motor: Engine = None):
    """
    Carga FACT_SERVICIOS de forma segura.
    - Sin method='multi' para evitar el error 9h9h de SQLAlchemy/PostgreSQL.
    - chunksize=500 para mantener el número de parámetros muy por debajo del límite de 32,000.
    """
    logger.info("Cargando FACT_SERVICIOS (modo seguro, chunksize=500, sin method='multi')...")
    motor = motor or MOTOR_BODEGA

    # 1. Crear tabla
    with motor.begin() as conn:
        conn.execute(text(DDL_FACT_SERVICIOS))
    logger.info("  ✅ Tabla creada")

    # 2. Cargar en lotes seguros
    total = len(df)
    chunksize = 500
    
    for i in range(0, total, chunksize):
        chunk = df.iloc[i:i + chunksize]
        try:
            chunk.to_sql(
                "fact_servicios",
                motor,
                if_exists="append",
                index=False,
                schema="public",
                chunksize=chunksize,  # Sin method='multi'
            )
            cargadas = i + len(chunk)
            progreso = (cargadas / total) * 100
            logger.info(f"  ✅ Lote cargado: {cargadas}/{total} ({progreso:.1f}%)")
        except Exception as e:
            logger.error(f"  ❌ Error en lote {i}-{i+len(chunk)}: {e}")
            raise
    
    logger.info(f"  -> {total} filas cargadas en total ✅")


# ============================================================
# ORQUESTADOR
# ============================================================
def ejecutar_fact_servicios():
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE: FACT_SERVICIOS")
    logger.info("=" * 60)

    datos = extraer()
    mapeos = _construir_mapeos_sk(MOTOR_BODEGA)
    fact = transformar(datos, mapeos)
    cargar(fact)

    logger.info("PIPELINE FACT_SERVICIOS COMPLETADO ✅")
    return fact


if __name__ == "__main__":
    ejecutar_fact_servicios()