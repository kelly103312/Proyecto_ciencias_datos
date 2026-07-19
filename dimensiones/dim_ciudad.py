"""
dim_ciudad.py
=============
Dimensión CIUDAD: permite análisis geográfico de la operación.
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
SQL_CIUDADES = """
    SELECT
        ci.ciudad_id          AS id_ciudad_ops,
        ci.nombre             AS nombre_ciudad,
        d.nombre              AS departamento
    FROM public.ciudad ci
    LEFT JOIN public.departamento d ON d.departamento_id = ci.departamento_id;
"""


def extraer(motor: Engine = None) -> pd.DataFrame:
    logger.info("Extrayendo DIM_CIUDAD...")
    motor = motor or MOTOR_ORIGEN
    df = pd.read_sql(SQL_CIUDADES, motor)
    logger.info(f"  -> {len(df)} filas extraídas")
    return df


# ============================================================
# 2. TRANSFORM
# ============================================================
def transformar(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transformando DIM_CIUDAD...")
    dim = df.copy()
    dim["id_ciudad"] = range(1, len(dim) + 1)

    dim = dim[[
        "id_ciudad", "id_ciudad_ops", "nombre_ciudad", "departamento",
    ]].copy()

    dim = dim.fillna({"departamento": "N/A"})

    desconocido = pd.DataFrame([{
        "id_ciudad": 0, "id_ciudad_ops": 0,
        "nombre_ciudad": "Desconocida", "departamento": "N/A",
    }])
    dim = pd.concat([desconocido, dim], ignore_index=True)

    logger.info(f"  -> {len(dim)} filas transformadas")
    return dim


# ============================================================
# 3. LOAD
# ============================================================
DDL_DIM_CIUDAD = """
DROP TABLE IF EXISTS dim_ciudad CASCADE;
CREATE TABLE dim_ciudad (
    id_ciudad INTEGER PRIMARY KEY,
    id_ciudad_ops INTEGER,
    nombre_ciudad VARCHAR(150),
    departamento VARCHAR(150)
);
"""


def cargar(df: pd.DataFrame, motor: Engine = None):
    logger.info("Cargando DIM_CIUDAD...")
    motor = motor or MOTOR_BODEGA

    with motor.begin() as conn:
        conn.execute(text(DDL_DIM_CIUDAD))

    df.to_sql(
        "dim_ciudad", motor, if_exists="append",
        index=False, schema="public", method="multi", chunksize=1000,
    )
    logger.info(f"  -> {len(df)} filas cargadas")


# ============================================================
# ORQUESTADOR
# ============================================================
def ejecutar_dim_ciudad():
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE: DIM_CIUDAD")
    logger.info("=" * 60)

    df_crudo = extraer()
    df_transformado = transformar(df_crudo)
    cargar(df_transformado)

    logger.info("PIPELINE DIM_CIUDAD COMPLETADO")
    return df_transformado


if __name__ == "__main__":
    ejecutar_dim_ciudad()