"""
dim_tiempo.py
=============
Dimensión TIEMPO: se GENERA por rango de fechas.
Contiene: EXTRACT, TRANSFORM y LOAD.
"""
import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text
from utils import MOTOR_BODEGA, get_logger
from config import FESTIVOS_COLOMBIA

logger = get_logger(__name__)


# ============================================================
# 1. EXTRACT (Generación de fechas)
# ============================================================
def extraer(fecha_min: str, fecha_max: str) -> pd.DataFrame:
    """
    Genera un rango de fechas desde fecha_min hasta fecha_max
    
    """
    logger.info(f"Generando rango de fechas: {fecha_min} a {fecha_max}")
    fechas = pd.date_range(start=fecha_min, end=fecha_max, freq="D")
    df = pd.DataFrame({"fecha_completa": fechas})
    logger.info(f"  -> {len(df)} fechas generadas")
    return df


# ============================================================
# 2. TRANSFORM
# ============================================================
def transformar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enriquece cada fecha con atributos temporales (día, mes, año, festivo, etc.).
    """
    logger.info("Transformando DIM_TIEMPO...")
    dim = df.copy()

    nombres_mes = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    nombres_dia = [
        "Lunes", "Martes", "Miércoles", "Jueves",
        "Viernes", "Sábado", "Domingo",
    ]

    registros = []
    for i, fecha in enumerate(dim["fecha_completa"], start=1):
        fecha_str = fecha.strftime("%Y-%m-%d")
        es_festivo = fecha_str in FESTIVOS_COLOMBIA

        registros.append({
            "id_tiempo": i,
            "fecha_completa": fecha.date(),
            "hora": None,
            "nombre_dia": nombres_dia[fecha.weekday()],
            "numero_dia_semana": fecha.isoweekday(),
            "dia_mes": fecha.day,
            "semana_anio": fecha.isocalendar()[1],
            "mes": fecha.month,
            "nombre_mes": nombres_mes[fecha.month - 1],
            "trimestre_anio": (fecha.month - 1) // 3 + 1,
            "anio": fecha.year,
            "es_festivo": es_festivo,
            "nombre_festividad": FESTIVOS_COLOMBIA.get(fecha_str, None),
        })

    dim_tiempo = pd.DataFrame(registros)

    # Fila "desconocido" (SK = 0)
    desconocido = pd.DataFrame([{
        "id_tiempo": 0, "fecha_completa": None, "hora": None,
        "nombre_dia": "Desconocido", "numero_dia_semana": 0,
        "dia_mes": 0, "semana_anio": 0, "mes": 0,
        "nombre_mes": "Desconocido", "trimestre_anio": 0, "anio": 0,
        "es_festivo": False, "nombre_festividad": None,
    }])
    dim_tiempo = pd.concat([desconocido, dim_tiempo], ignore_index=True)

    logger.info(f"  -> {len(dim_tiempo)} filas transformadas")
    return dim_tiempo


# ============================================================
# 3. LOAD
# ============================================================
DDL_DIM_TIEMPO = """
DROP TABLE IF EXISTS dim_tiempo CASCADE;
CREATE TABLE dim_tiempo (
    id_tiempo INTEGER PRIMARY KEY,
    fecha_completa DATE,
    hora INTEGER,
    nombre_dia VARCHAR(20),
    numero_dia_semana INTEGER,
    dia_mes INTEGER,
    semana_anio INTEGER,
    mes INTEGER,
    nombre_mes VARCHAR(20),
    trimestre_anio INTEGER,
    anio INTEGER,
    es_festivo BOOLEAN,
    nombre_festividad VARCHAR(100)
);
"""


def cargar(df: pd.DataFrame, motor: Engine = None):
    """Carga DIM_TIEMPO en la bodega."""
    logger.info("Cargando DIM_TIEMPO...")
    motor = motor or MOTOR_BODEGA

    with motor.begin() as conn:
        conn.execute(text(DDL_DIM_TIEMPO))

    df.to_sql(
        "dim_tiempo", motor, if_exists="append",
        index=False, schema="public", method="multi", chunksize=1000,
    )
    logger.info(f"  -> {len(df)} filas cargadas")


# ============================================================
# ORQUESTADOR
# ============================================================
def ejecutar_dim_tiempo(fecha_min: str, fecha_max: str):
    """Ejecuta el pipeline completo de DIM_TIEMPO."""
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE: DIM_TIEMPO")
    logger.info("=" * 60)

    df_crudo = extraer(fecha_min, fecha_max)
    df_transformado = transformar(df_crudo)
    cargar(df_transformado)

    logger.info("PIPELINE DIM_TIEMPO COMPLETADO")
    return df_transformado


if __name__ == "__main__":
    ejecutar_dim_tiempo("2024-01-01", "2026-12-31")