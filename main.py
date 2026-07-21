"""
main.py
=======
Orquestador principal del pipeline ETL modularizado.
Ejecuta las dimensiones en orden y luego la tabla de hechos.
"""
from dimensiones import (
    dim_tiempo, dim_cliente, dim_ciudad, dim_sede,
    dim_mensajero, dim_tipo_entrega, dim_categoria_servicio,
    dim_novedad, dim_tipo_vehiculo,
)
from hechos import fact_servicios, fact_novedades
from utils import get_logger, MOTOR_ORIGEN
import pandas as pd

logger = get_logger("ETL_MAIN")


def obtener_rango_fechas() -> tuple:
    """
    Determina el rango de fechas a generar en DIM_TIEMPO.

    NOTA: fecha_deseada se excluye a propósito. Tiene valores corruptos en la BD
    operacional (ej. años 0004 y 9024) que distorsionarían el rango y harían que
    DIM_TIEMPO. Los servicios con fecha_deseada corrupta quedará en 0 ("Desconocido").
    """
    sql = """
        SELECT MIN(f) AS min_fecha, MAX(f) AS max_fecha
        FROM (
            SELECT fecha_solicitud AS f FROM public.mensajeria_servicio WHERE es_prueba = FALSE
            UNION ALL
            SELECT fecha AS f FROM public.mensajeria_estadosservicio WHERE es_prueba = FALSE
        ) fechas;
    """
    df = pd.read_sql(sql, MOTOR_ORIGEN)
    min_f = df["min_fecha"].iloc[0]
    max_f = df["max_fecha"].iloc[0]
    return str(min_f), str(max_f)


def ejecutar_etl_completo():
    """Ejecuta el pipeline ETL completo en el orden correcto."""
    try:
        logger.info("INICIO DEL PIPELINE ETL - Fast and Safe")
        logger.info("=" * 60)

        # 1. Determinar rango de fechas
        fecha_min, fecha_max = obtener_rango_fechas()
        logger.info(f"Rango de fechas detectado: {fecha_min} a {fecha_max}")

        # 2. Cargar dimensiones (en orden de independencia)
        logger.info("\nCARGANDO DIMENSIONES")
        logger.info("-" * 60)

        dim_tiempo.ejecutar_dim_tiempo(fecha_min, fecha_max)
        dim_cliente.ejecutar_dim_cliente()
        dim_ciudad.ejecutar_dim_ciudad()
        dim_sede.ejecutar_dim_sede()
        dim_mensajero.ejecutar_dim_mensajero()
        dim_tipo_entrega.ejecutar_dim_tipo_entrega()
        dim_categoria_servicio.ejecutar_dim_categoria_servicio()  # NUEVA (A1)
        dim_novedad.ejecutar_dim_novedad()
        dim_tipo_vehiculo.ejecutar_dim_tipo_vehiculo()

        # 3. Cargar hechos (al final, depende de todas las dimensiones)
        logger.info("\nCARGANDO HECHOS")
        logger.info("-" * 60)

        fact_servicios.ejecutar_fact_servicios()
        fact_novedades.ejecutar_fact_novedades()  # NUEVA (A2) — no depende de fact_servicios

        logger.info("=" * 60)
        logger.info("PIPELINE ETL FINALIZADO CON ÉXITO")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"FALLÓ EL PIPELINE ETL: {e}")
        raise


if __name__ == "__main__":
    ejecutar_etl_completo()