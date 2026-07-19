"""
dim_categoria_servicio.py
==========================
Dimensión CATEGORÍA DE SERVICIO: clasifica los servicios por su naturaleza de negocio
(Administrativo, Comercial, Clínico, Urgencia Vital).

Nace de separar dos conceptos que estaban mezclados bajo DIM_TIPO_ENTREGA:
esta dimensión captura la CATEGORÍA del servicio (antes en DIM_TIPO_ENTREGA,
mapeada por error), mientras que DIM_TIPO_ENTREGA ahora captura el SLA real
(columna `prioridad`). Ver Modificaciones/Seccion A1.md.

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
SQL_CATEGORIAS_SERVICIO = """
    SELECT
        id                    AS id_categoria_servicio_ops,
        nombre                AS categoria_servicio,
        descripcion
    FROM public.mensajeria_tiposervicio;
"""


def extraer(motor: Engine = None) -> pd.DataFrame:
    logger.info("Extrayendo DIM_CATEGORIA_SERVICIO...")
    motor = motor or MOTOR_ORIGEN
    df = pd.read_sql(SQL_CATEGORIAS_SERVICIO, motor)
    logger.info(f"  -> {len(df)} filas extraídas")
    return df


# ============================================================
# 2. TRANSFORM
# ============================================================
def transformar(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transformando DIM_CATEGORIA_SERVICIO...")
    dim = df.copy()
    dim["id_categoria_servicio"] = range(1, len(dim) + 1)

    dim = dim[[
        "id_categoria_servicio", "id_categoria_servicio_ops",
        "categoria_servicio", "descripcion",
    ]].copy()

    desconocido = pd.DataFrame([{
        "id_categoria_servicio": 0, "id_categoria_servicio_ops": 0,
        "categoria_servicio": "Desconocido", "descripcion": "N/A",
    }])
    dim = pd.concat([desconocido, dim], ignore_index=True)

    logger.info(f"  -> {len(dim)} filas transformadas")
    return dim


# ============================================================
# 3. LOAD
# ============================================================
DDL_DIM_CATEGORIA_SERVICIO = """
DROP TABLE IF EXISTS dim_categoria_servicio CASCADE;
CREATE TABLE dim_categoria_servicio (
    id_categoria_servicio INTEGER PRIMARY KEY,
    id_categoria_servicio_ops INTEGER,
    categoria_servicio VARCHAR(100),
    descripcion VARCHAR(500)
);
"""


def cargar(df: pd.DataFrame, motor: Engine = None):
    logger.info("Cargando DIM_CATEGORIA_SERVICIO...")
    motor = motor or MOTOR_BODEGA

    with motor.begin() as conn:
        conn.execute(text(DDL_DIM_CATEGORIA_SERVICIO))

    df.to_sql(
        "dim_categoria_servicio", motor, if_exists="append",
        index=False, schema="public", method="multi", chunksize=1000,
    )
    logger.info(f"  -> {len(df)} filas cargadas")


# ============================================================
# ORQUESTADOR
# ============================================================
def ejecutar_dim_categoria_servicio():
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE: DIM_CATEGORIA_SERVICIO")
    logger.info("=" * 60)

    df_crudo = extraer()
    df_transformado = transformar(df_crudo)
    cargar(df_transformado)

    logger.info("PIPELINE DIM_CATEGORIA_SERVICIO COMPLETADO")
    return df_transformado


if __name__ == "__main__":
    ejecutar_dim_categoria_servicio()
