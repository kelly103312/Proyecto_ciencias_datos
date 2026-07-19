"""
fact_novedades.py
==================
Tabla de hechos NOVEDADES: registra cada novedad ocurrida durante la prestación
de un servicio. Grano: 1 fila = 1 novedad ocurrida (no 1 por servicio).

Nace de una limitación de FACT_SERVICIOS: por su grano (1 fila por servicio),
solo puede capturar la primera novedad de cada servicio, descartando las demás.
Ver Modificaciones/Seccion A2.md para la justificación completa.

`id_servicio` es una columna degenerada: coincide exactamente con
FACT_SERVICIOS.id_hecho (ambos son mensajeria_servicio.id, sin renumerar), así
que no requiere mapeo ni depende de que FACT_SERVICIOS ya esté cargado — solo
necesita que dim_tiempo, dim_novedad y dim_mensajero existan.

Contiene: EXTRACT, TRANSFORM y LOAD.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text
from utils import MOTOR_ORIGEN, MOTOR_BODEGA, get_logger

logger = get_logger(__name__)


# ============================================================
# 1. EXTRACT
# ============================================================
SQL_NOVEDADES = """
    SELECT
        n.servicio_id,
        n.fecha_novedad,
        n.tipo_novedad_id,
        n.mensajero_id,
        n.descripcion
    FROM public.mensajeria_novedadesservicio n
    WHERE n.es_prueba = FALSE;
"""


def extraer(motor: Engine = None) -> pd.DataFrame:
    logger.info("Extrayendo FACT_NOVEDADES...")
    motor = motor or MOTOR_ORIGEN
    df = pd.read_sql(SQL_NOVEDADES, motor)
    logger.info(f"  -> {len(df)} filas extraídas")
    return df


# ============================================================
# 2. TRANSFORM
# ============================================================
def _construir_mapeos_sk(motor_bodega: Engine) -> dict:
    logger.info("Construyendo mapeos de SK para FACT_NOVEDADES...")

    def leer(tabla, col_ops, col_sk):
        df = pd.read_sql(f"SELECT {col_ops}, {col_sk} FROM {tabla}", motor_bodega)
        return dict(zip(df[col_ops].astype(int), df[col_sk].astype(int)))

    mapeos = {
        "novedad": leer("dim_novedad", "id_novedad_ops", "id_novedad"),
        "mensajero": leer("dim_mensajero", "id_mensajero_ops", "id_mensajero"),
    }
    df_t = pd.read_sql("SELECT fecha_completa, id_tiempo FROM dim_tiempo WHERE id_tiempo > 0", motor_bodega)
    mapeos["tiempo"] = dict(zip(df_t["fecha_completa"], df_t["id_tiempo"]))
    logger.info(f"  -> {len(mapeos['tiempo'])} fechas mapeadas")
    return mapeos


def transformar(df: pd.DataFrame, mapeos: dict) -> pd.DataFrame:
    logger.info("Transformando FACT_NOVEDADES...")
    fact = df.copy()

    def mapear(valor, mapeo, default=0):
        if pd.isna(valor):
            return default
        try:
            return mapeo.get(int(valor), default)
        except (ValueError, TypeError):
            return default

    fact["fecha_novedad_dt"] = pd.to_datetime(fact["fecha_novedad"], errors="coerce")
    fact["id_tiempo"] = fact["fecha_novedad_dt"].dt.date.apply(
        lambda d: mapeos["tiempo"].get(d, 0) if pd.notna(d) else 0)
    fact["id_novedad"] = fact["tipo_novedad_id"].apply(lambda x: mapear(x, mapeos["novedad"]))
    fact["id_mensajero"] = fact["mensajero_id"].apply(lambda x: mapear(x, mapeos["mensajero"]))
    # Degenerada: mismo valor que FACT_SERVICIOS.id_hecho, no requiere mapeo.
    fact["id_servicio"] = pd.to_numeric(fact["servicio_id"], errors="coerce").fillna(0).astype(int)

    fact["descripcion_novedad"] = (fact["descripcion"]
        .fillna("N/A").astype(str)
        .str.replace('\x00', '', regex=False)
        .str[:700])

    columnas_fact = [
        "id_servicio", "id_tiempo", "id_novedad", "id_mensajero", "descripcion_novedad",
    ]
    fact_final = fact[columnas_fact].copy()
    fact_final.insert(0, "sk_novedad", range(1, len(fact_final) + 1))

    int_cols = ["sk_novedad", "id_servicio", "id_tiempo", "id_novedad", "id_mensajero"]
    for col in int_cols:
        fact_final[col] = pd.to_numeric(fact_final[col], errors="coerce").fillna(0).astype(int)

    logger.info(f"  -> {len(fact_final)} filas transformadas")
    return fact_final


# ============================================================
# 3. LOAD
# ============================================================
DDL_FACT_NOVEDADES = """
DROP TABLE IF EXISTS fact_novedades CASCADE;
CREATE TABLE fact_novedades (
    sk_novedad INTEGER PRIMARY KEY,
    id_servicio INTEGER,
    id_tiempo INTEGER,
    id_novedad INTEGER,
    id_mensajero INTEGER,
    descripcion_novedad VARCHAR(700)
);
"""


def cargar(df: pd.DataFrame, motor: Engine = None):
    logger.info("Cargando FACT_NOVEDADES...")
    motor = motor or MOTOR_BODEGA

    with motor.begin() as conn:
        conn.execute(text(DDL_FACT_NOVEDADES))

    df.to_sql(
        "fact_novedades", motor, if_exists="append",
        index=False, schema="public", method="multi", chunksize=1000,
    )
    logger.info(f"  -> {len(df)} filas cargadas")


# ============================================================
# ORQUESTADOR
# ============================================================
def ejecutar_fact_novedades():
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE: FACT_NOVEDADES")
    logger.info("=" * 60)

    df_crudo = extraer()
    mapeos = _construir_mapeos_sk(MOTOR_BODEGA)
    fact = transformar(df_crudo, mapeos)
    cargar(fact)

    logger.info("PIPELINE FACT_NOVEDADES COMPLETADO")
    return fact


if __name__ == "__main__":
    ejecutar_fact_novedades()
