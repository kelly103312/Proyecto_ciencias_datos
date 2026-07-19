"""
dim_tipo_entrega.py
===================
Dimensión TIPO ENTREGA: clasifica los servicios según el SLA de entrega
(Alta/Media/Baja) prometido al cliente.

Se construye desde la columna `prioridad` de mensajeria_servicio, que es texto
libre sin catálogo (ej. "Alta: En una Hora", "Media: De 1 - 3 Horas"). Se
normaliza con utils.normalizar_prioridad() para colapsar variantes de
redacción ("Alta: En una Hora" / "Alta: En una hora") al mismo valor.

Antes, esta dimensión se construía por error desde `mensajeria_tiposervicio`
(categoría de negocio, no SLA) — ver Modificaciones/Seccion A1.md. Esa
categoría ahora vive en DIM_CATEGORIA_SERVICIO.

Contiene: EXTRACT, TRANSFORM y LOAD.
"""
import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text
from utils import MOTOR_ORIGEN, MOTOR_BODEGA, get_logger, normalizar_prioridad

logger = get_logger(__name__)


# ============================================================
# 1. EXTRACT
# ============================================================
SQL_PRIORIDADES = """
    SELECT DISTINCT prioridad
    FROM public.mensajeria_servicio
    WHERE es_prueba = FALSE AND prioridad IS NOT NULL;
"""


def extraer(motor: Engine = None) -> pd.DataFrame:
    logger.info("Extrayendo DIM_TIPO_ENTREGA...")
    motor = motor or MOTOR_ORIGEN
    df = pd.read_sql(SQL_PRIORIDADES, motor)
    logger.info(f"  -> {len(df)} valores distintos de prioridad extraídos")
    return df


# ============================================================
# 2. TRANSFORM
# ============================================================
def transformar(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transformando DIM_TIPO_ENTREGA...")
    dim = df.copy()
    dim["sla"] = dim["prioridad"].apply(normalizar_prioridad)

    # Colapsar variantes de redacción ("Alta: En una Hora" / "Alta: En una hora")
    # al mismo valor canónico antes de asignar la llave subrogada.
    dim = dim.drop_duplicates(subset=["sla"])[["sla"]].reset_index(drop=True)
    dim["id_tipo_entrega"] = range(1, len(dim) + 1)
    dim = dim[["id_tipo_entrega", "sla"]].copy()

    desconocido = pd.DataFrame([{
        "id_tipo_entrega": 0, "sla": "Desconocido",
    }])
    dim = pd.concat([desconocido, dim], ignore_index=True)

    logger.info(f"  -> {len(dim)} filas transformadas: {dim['sla'].tolist()}")
    return dim


# ============================================================
# 3. LOAD
# ============================================================
DDL_DIM_TIPO_ENTREGA = """
DROP TABLE IF EXISTS dim_tipo_entrega CASCADE;
CREATE TABLE dim_tipo_entrega (
    id_tipo_entrega INTEGER PRIMARY KEY,
    sla VARCHAR(50)
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
