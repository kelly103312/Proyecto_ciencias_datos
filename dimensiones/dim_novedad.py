"""
dim_novedad.py
==============
Dimensión NOVEDAD: tipifica las interrupciones durante el servicio.
Contiene: EXTRACT, TRANSFORM y LOAD.
"""
import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text
from utils import MOTOR_ORIGEN, MOTOR_BODEGA, get_logger

logger = get_logger(__name__)


# ============================================================
# 1. EXTRACT
# ============================================================
SQL_TIPOS_NOVEDAD = """
    SELECT
        id                    AS id_novedad_ops,
        nombre                AS tipo_novedad
    FROM public.mensajeria_tiponovedad;
"""


def extraer(motor: Engine = None) -> pd.DataFrame:
    logger.info("Extrayendo DIM_NOVEDAD...")
    motor = motor or MOTOR_ORIGEN
    df = pd.read_sql(SQL_TIPOS_NOVEDAD, motor)
    logger.info(f"  -> {len(df)} filas extraídas")
    return df


# ============================================================
# 2. TRANSFORM
# ============================================================
def transformar(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transformando DIM_NOVEDAD...")
    dim = df.copy()
    dim["id_novedad"] = range(1, len(dim) + 1)

    dim = dim[["id_novedad", "id_novedad_ops", "tipo_novedad"]].copy()

    desconocido = pd.DataFrame([{
        "id_novedad": 0, "id_novedad_ops": 0, "tipo_novedad": "Sin novedad",
    }])
    dim = pd.concat([desconocido, dim], ignore_index=True)

    logger.info(f"  -> {len(dim)} filas transformadas")
    return dim


# ============================================================
# 3. LOAD
# ============================================================
DDL_DIM_NOVEDAD = """
DROP TABLE IF EXISTS dim_novedad CASCADE;
CREATE TABLE dim_novedad (
    id_novedad INTEGER PRIMARY KEY,
    id_novedad_ops INTEGER,
    tipo_novedad VARCHAR(100)
);
"""


def cargar(df: pd.DataFrame, motor: Engine = None):
    logger.info("Cargando DIM_NOVEDAD...")
    motor = motor or MOTOR_BODEGA

    with motor.begin() as conn:
        conn.execute(text(DDL_DIM_NOVEDAD))

    df.to_sql(
        "dim_novedad", motor, if_exists="append",
        index=False, schema="public", method="multi", chunksize=1000,
    )
    logger.info(f"  -> {len(df)} filas cargadas ✅")


# ============================================================
# ORQUESTADOR
# ============================================================
def ejecutar_dim_novedad():
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE: DIM_NOVEDAD")
    logger.info("=" * 60)

    df_crudo = extraer()
    df_transformado = transformar(df_crudo)
    cargar(df_transformado)

    logger.info("PIPELINE DIM_NOVEDAD COMPLETADO ✅")
    return df_transformado


if __name__ == "__main__":
    ejecutar_dim_novedad()