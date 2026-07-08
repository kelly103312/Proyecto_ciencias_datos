"""
dim_tipo_entrega.py
===================
Dimensión TIPO ENTREGA: clasifica los servicios según SLA.
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
SQL_TIPOS_SERVICIO = """
    SELECT
        id                    AS id_tipo_entrega_ops,
        nombre,
        descripcion
    FROM public.mensajeria_tiposervicio;
"""


def extraer(motor: Engine = None) -> pd.DataFrame:
    logger.info("Extrayendo DIM_TIPO_ENTREGA...")
    motor = motor or MOTOR_ORIGEN
    df = pd.read_sql(SQL_TIPOS_SERVICIO, motor)
    logger.info(f"  -> {len(df)} filas extraídas")
    return df


# ============================================================
# 2. TRANSFORM
# ============================================================
def transformar(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transformando DIM_TIPO_ENTREGA...")
    dim = df.copy()
    dim["id_tipo_entrega"] = range(1, len(dim) + 1)

    dim = dim[[
        "id_tipo_entrega", "id_tipo_entrega_ops", "nombre", "descripcion",
    ]].copy()
    dim = dim.rename(columns={"nombre": "tipo_entrega"})

    desconocido = pd.DataFrame([{
        "id_tipo_entrega": 0, "id_tipo_entrega_ops": 0,
        "tipo_entrega": "Desconocido", "descripcion": "N/A",
    }])
    dim = pd.concat([desconocido, dim], ignore_index=True)

    logger.info(f"  -> {len(dim)} filas transformadas")
    return dim


# ============================================================
# 3. LOAD
# ============================================================
DDL_DIM_TIPO_ENTREGA = """
DROP TABLE IF EXISTS dim_tipo_entrega CASCADE;
CREATE TABLE dim_tipo_entrega (
    id_tipo_entrega INTEGER PRIMARY KEY,
    id_tipo_entrega_ops INTEGER,
    tipo_entrega VARCHAR(100),
    descripcion VARCHAR(500)
);
"""


def cargar(df: pd.DataFrame, motor: Engine = None):
    logger.info("Cargando DIM_TIPO_ENTREGA...")
    motor = motor or MOTOR_BODEGA

    with motor.begin() as conn:
        conn.execute(text(DDL_DIM_TIPO_ENTREGA))

    df.to_sql(
        "dim_tipo_entrega", motor, if_exists="append",
        index=False, schema="public", method="multi", chunksize=1000,
    )
    logger.info(f"  -> {len(df)} filas cargadas ✅")


# ============================================================
# ORQUESTADOR
# ============================================================
def ejecutar_dim_tipo_entrega():
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE: DIM_TIPO_ENTREGA")
    logger.info("=" * 60)

    df_crudo = extraer()
    df_transformado = transformar(df_crudo)
    cargar(df_transformado)

    logger.info("PIPELINE DIM_TIPO_ENTREGA COMPLETADO ✅")
    return df_transformado


if __name__ == "__main__":
    ejecutar_dim_tipo_entrega()