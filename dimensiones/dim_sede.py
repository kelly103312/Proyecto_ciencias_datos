"""
dim_sede.py
===========
Dimensión SEDE: ubicaciones físicas de los clientes.
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
SQL_SEDES = """
    SELECT
        s.sede_id             AS id_sede_ops,
        s.nombre,
        s.direccion,
        s.telefono,
        s.nombre_contacto,
        s.cliente_id,
        s.ciudad_id
    FROM public.sede s;
"""


def extraer(motor: Engine = None) -> pd.DataFrame:
    logger.info("Extrayendo DIM_SEDE...")
    motor = motor or MOTOR_ORIGEN
    df = pd.read_sql(SQL_SEDES, motor)
    logger.info(f"  -> {len(df)} filas extraídas")
    return df


# ============================================================
# 2. TRANSFORM
# ============================================================
def transformar(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transformando DIM_SEDE...")
    dim = df.copy()
    dim["id_sede"] = range(1, len(dim) + 1)

    dim = dim[[
        "id_sede", "id_sede_ops", "nombre", "direccion",
        "telefono", "nombre_contacto", "cliente_id", "ciudad_id",
    ]].copy()

    dim = dim.fillna({"telefono": "N/A", "nombre_contacto": "N/A"})

    desconocido = pd.DataFrame([{
        "id_sede": 0, "id_sede_ops": 0, "nombre": "Desconocida",
        "direccion": "N/A", "telefono": "N/A", "nombre_contacto": "N/A",
        "cliente_id": 0, "ciudad_id": 0,
    }])
    dim = pd.concat([desconocido, dim], ignore_index=True)

    logger.info(f"  -> {len(dim)} filas transformadas")
    return dim


# ============================================================
# 3. LOAD
# ============================================================
DDL_DIM_SEDE = """
DROP TABLE IF EXISTS dim_sede CASCADE;
CREATE TABLE dim_sede (
    id_sede INTEGER PRIMARY KEY,
    id_sede_ops INTEGER,
    nombre VARCHAR(200),
    direccion VARCHAR(300),
    telefono VARCHAR(50),
    nombre_contacto VARCHAR(150),
    cliente_id INTEGER,
    ciudad_id INTEGER
);
"""


def cargar(df: pd.DataFrame, motor: Engine = None):
    logger.info("Cargando DIM_SEDE...")
    motor = motor or MOTOR_BODEGA

    with motor.begin() as conn:
        conn.execute(text(DDL_DIM_SEDE))

    df.to_sql(
        "dim_sede", motor, if_exists="append",
        index=False, schema="public", method="multi", chunksize=1000,
    )
    logger.info(f"  -> {len(df)} filas cargadas ✅")


# ============================================================
# ORQUESTADOR
# ============================================================
def ejecutar_dim_sede():
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE: DIM_SEDE")
    logger.info("=" * 60)

    df_crudo = extraer()
    df_transformado = transformar(df_crudo)
    cargar(df_transformado)

    logger.info("PIPELINE DIM_SEDE COMPLETADO ✅")
    return df_transformado


if __name__ == "__main__":
    ejecutar_dim_sede()