"""
dim_mensajero.py
================
Dimensión MENSAJERO: colaboradores operativos encargados de la entrega.
Contiene: EXTRACT, TRANSFORM y LOAD.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text
from utils import get_logger, MOTOR_ORIGEN, MOTOR_BODEGA

logger = get_logger(__name__)


# ============================================================
# 1. EXTRACT
# ============================================================
SQL_MENSAJEROS = """
    SELECT
        m.id                  AS id_mensajero_ops,
        m.user_id,
        u.first_name          AS nombre,
        u.last_name           AS apellido,
        m.telefono,
        m.activo,
        m.fecha_entrada,
        m.fecha_salida,
        m.ciudad_operacion_id
    FROM public.clientes_mensajeroaquitoy m
    INNER JOIN public.auth_user u ON u.id = m.user_id;
"""


def extraer(motor: Engine = None) -> pd.DataFrame:
    logger.info("Extrayendo DIM_MENSAJERO...")
    motor = motor or MOTOR_ORIGEN
    df = pd.read_sql(SQL_MENSAJEROS, motor)
    logger.info(f"  -> {len(df)} filas extraídas")
    return df


# ============================================================
# 2. TRANSFORM
# ============================================================
def transformar(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transformando DIM_MENSAJERO...")
    dim = df.copy()
    dim["id_mensajero"] = range(1, len(dim) + 1)

    dim = dim[[
        "id_mensajero", "id_mensajero_ops", "nombre", "apellido",
        "telefono", "activo", "fecha_entrada", "fecha_salida",
        "ciudad_operacion_id",
    ]].copy()

    dim = dim.fillna({"apellido": "N/A", "telefono": "N/A", "fecha_salida": None})

    # Estado derivado
    dim["estado"] = dim.apply(
        lambda r: "Activo" if r["activo"] else "Inactivo", axis=1
    )

    desconocido = pd.DataFrame([{
        "id_mensajero": 0, "id_mensajero_ops": 0,
        "nombre": "Desconocido", "apellido": "N/A",
        "telefono": "N/A", "activo": False,
        "fecha_entrada": None, "fecha_salida": None,
        "ciudad_operacion_id": 0, "estado": "Desconocido",
    }])
    dim = pd.concat([desconocido, dim], ignore_index=True)

    logger.info(f"  -> {len(dim)} filas transformadas")
    return dim


# ============================================================
# 3. LOAD
# ============================================================
DDL_DIM_MENSAJERO = """
DROP TABLE IF EXISTS dim_mensajero CASCADE;
CREATE TABLE dim_mensajero (
    id_mensajero INTEGER PRIMARY KEY,
    id_mensajero_ops INTEGER,
    nombre VARCHAR(100),
    apellido VARCHAR(100),
    telefono VARCHAR(30),
    activo BOOLEAN,
    fecha_entrada DATE,
    fecha_salida DATE,
    ciudad_operacion_id INTEGER,
    estado VARCHAR(20)
);
"""


def cargar(df: pd.DataFrame, motor: Engine = None):
    logger.info("Cargando DIM_MENSAJERO...")
    motor = motor or MOTOR_BODEGA

    with motor.begin() as conn:
        conn.execute(text(DDL_DIM_MENSAJERO))

    df.to_sql(
        "dim_mensajero", motor, if_exists="append",
        index=False, schema="public", method="multi", chunksize=1000,
    )
    logger.info(f"  -> {len(df)} filas cargadas ✅")


# ============================================================
# ORQUESTADOR
# ============================================================
def ejecutar_dim_mensajero():
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE: DIM_MENSAJERO")
    logger.info("=" * 60)

    df_crudo = extraer()
    df_transformado = transformar(df_crudo)
    cargar(df_transformado)

    logger.info("PIPELINE DIM_MENSAJERO COMPLETADO ✅")
    return df_transformado


if __name__ == "__main__":
    ejecutar_dim_mensajero()