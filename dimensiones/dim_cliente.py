"""
dim_cliente.py
==============
Dimensión CLIENTE: empresas que contratan los servicios de mensajería.
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
SQL_CLIENTES = """
    SELECT
        c.cliente_id          AS id_cliente_ops,
        c.nit_cliente,
        c.nombre,
        c.nombre_contacto,
        c.sector,
        c.activo,
        c.tipo_cliente_id,
        tc.nombre             AS tipo_cliente
    FROM public.cliente c
    LEFT JOIN public.tipo_cliente tc ON tc.tipo_cliente_id = c.tipo_cliente_id;
"""


def extraer(motor: Engine = None) -> pd.DataFrame:
    logger.info("Extrayendo DIM_CLIENTE...")
    motor = motor or MOTOR_ORIGEN
    df = pd.read_sql(SQL_CLIENTES, motor)
    logger.info(f"  -> {len(df)} filas extraídas")
    return df


# ============================================================
# 2. TRANSFORM
# ============================================================
def transformar(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transformando DIM_CLIENTE...")
    dim = df.copy()
    dim["id_cliente"] = range(1, len(dim) + 1)

    dim = dim[[
        "id_cliente", "id_cliente_ops", "nombre", "nit_cliente",
        "nombre_contacto", "sector",
        "tipo_cliente", "activo",
    ]].copy()

    dim = dim.fillna({
        "nombre_contacto": "N/A", "sector": "N/A",
    })

    desconocido = pd.DataFrame([{
        "id_cliente": 0, "id_cliente_ops": 0, "nombre": "Desconocido",
        "nit_cliente": "N/A", 
        "nombre_contacto": "N/A", "sector": "N/A",
        "tipo_cliente": "N/A", "activo": True,
    }])
    dim = pd.concat([desconocido, dim], ignore_index=True)

    logger.info(f"  -> {len(dim)} filas transformadas")
    return dim


# ============================================================
# 3. LOAD
# ============================================================
DDL_DIM_CLIENTE = """
DROP TABLE IF EXISTS dim_cliente CASCADE;
CREATE TABLE dim_cliente (
    id_cliente INTEGER PRIMARY KEY,
    id_cliente_ops INTEGER,
    nombre VARCHAR(200),
    nit_cliente VARCHAR(50),
    nombre_contacto VARCHAR(150),
    sector VARCHAR(100),
    tipo_cliente VARCHAR(100),
    activo BOOLEAN
);
"""


def cargar(df: pd.DataFrame, motor: Engine = None):
    logger.info("Cargando DIM_CLIENTE...")
    motor = motor or MOTOR_BODEGA

    with motor.begin() as conn:
        conn.execute(text(DDL_DIM_CLIENTE))

    df.to_sql(
        "dim_cliente", motor, if_exists="append",
        index=False, schema="public", method="multi", chunksize=1000,
    )
    logger.info(f"  -> {len(df)} filas cargadas")


# ============================================================
# ORQUESTADOR
# ============================================================
def ejecutar_dim_cliente():
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE: DIM_CLIENTE")
    logger.info("=" * 60)

    df_crudo = extraer()
    df_transformado = transformar(df_crudo)
    cargar(df_transformado)

    logger.info("PIPELINE DIM_CLIENTE COMPLETADO")
    return df_transformado


if __name__ == "__main__":
    ejecutar_dim_cliente()