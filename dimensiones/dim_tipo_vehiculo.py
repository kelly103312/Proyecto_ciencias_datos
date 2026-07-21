"""
dim_tipo_vehiculo.py
====================
Dimensión TIPO VEHÍCULO: clasifica los vehículos usados en los servicios.
Permite análisis de eficiencia por tipo de vehículo (moto, bicicleta, auto).

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
SQL_TIPOS_VEHICULO = """
    SELECT
        id                    AS id_tipo_vehiculo_ops,
        nombre,
        descripcion
    FROM public.mensajeria_tipovehiculo;
"""


def extraer(motor: Engine = None) -> pd.DataFrame:
    """Extrae los tipos de vehículo desde la BD operacional."""
    logger.info("Extrayendo DIM_TIPO_VEHICULO...")
    motor = motor or MOTOR_ORIGEN
    df = pd.read_sql(SQL_TIPOS_VEHICULO, motor)
    logger.info(f"  -> {len(df)} filas extraídas")
    return df


# ============================================================
# 2. TRANSFORM
# ============================================================
def transformar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma los datos crudos en la estructura de DIM_TIPO_VEHICULO.
    Asigna surrogate key y agrega fila "desconocido".
    """
    logger.info("Transformando DIM_TIPO_VEHICULO...")
    dim = df.copy()

    # Asignar surrogate key
    dim["id_tipo_vehiculo"] = range(1, len(dim) + 1)

    # Selección de columnas finales
    dim = dim[[
        "id_tipo_vehiculo", "id_tipo_vehiculo_ops", "nombre", "descripcion",
    ]].copy()
    dim = dim.rename(columns={"nombre": "tipo_vehiculo"})

    # Manejo de nulos
    dim = dim.fillna({"descripcion": "N/A"})

    # Fila "desconocido" (SK = 0)
    desconocido = pd.DataFrame([{
        "id_tipo_vehiculo": 0,
        "id_tipo_vehiculo_ops": 0,
        "tipo_vehiculo": "Desconocido",
        "descripcion": "N/A",
    }])
    dim = pd.concat([desconocido, dim], ignore_index=True)

    logger.info(f"  -> {len(dim)} filas transformadas")
    return dim


# ============================================================
# 3. LOAD
# ============================================================
DDL_DIM_TIPO_VEHICULO = """
DROP TABLE IF EXISTS dim_tipo_vehiculo CASCADE;
CREATE TABLE dim_tipo_vehiculo (
    id_tipo_vehiculo INTEGER PRIMARY KEY,
    id_tipo_vehiculo_ops INTEGER,
    tipo_vehiculo VARCHAR(100),
    descripcion VARCHAR(500)
);
"""


def cargar(df: pd.DataFrame, motor: Engine = None):
    """Carga DIM_TIPO_VEHICULO en la bodega."""
    logger.info("Cargando DIM_TIPO_VEHICULO...")
    motor = motor or MOTOR_BODEGA

    # Crear tabla
    with motor.begin() as conn:
        conn.execute(text(DDL_DIM_TIPO_VEHICULO))

    # Insertar datos
    df.to_sql(
        "dim_tipo_vehiculo",
        motor,
        if_exists="append",
        index=False,
        schema="public",
        method="multi",
        chunksize=1000,
    )
    logger.info(f"  -> {len(df)} filas cargadas")


# ============================================================
# ORQUESTADOR
# ============================================================
def ejecutar_dim_tipo_vehiculo():
    """Ejecuta el pipeline completo de DIM_TIPO_VEHICULO."""
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE: DIM_TIPO_VEHICULO")
    logger.info("=" * 60)

    df_crudo = extraer()
    df_transformado = transformar(df_crudo)
    cargar(df_transformado)

    logger.info("PIPELINE DIM_TIPO_VEHICULO COMPLETADO")
    return df_transformado


if __name__ == "__main__":
    ejecutar_dim_tipo_vehiculo()