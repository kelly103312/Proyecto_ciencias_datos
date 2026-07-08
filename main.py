"""
main.py
=======
Orquestador principal del pipeline ETL modularizado.
Ejecuta las dimensiones en orden y luego la tabla de hechos.
"""
from dimensiones import (
    dim_tiempo, dim_cliente, dim_ciudad, dim_sede,
    dim_mensajero, dim_tipo_entrega, dim_novedad,
    dim_tipo_vehiculo,  # NUEVA DIMENSIÓN
)
from hechos import fact_servicios
from utils import get_logger, MOTOR_ORIGEN
import pandas as pd

logger = get_logger("ETL_MAIN")


def obtener_rango_fechas() -> tuple:
    """Determina el rango de fechas desde los servicios en la BD operacional."""
    sql = """
        SELECT MIN(fecha_solicitud) AS min_fecha, MAX(fecha_solicitud) AS max_fecha
        FROM public.mensajeria_servicio
        WHERE es_prueba = FALSE;
    """
    df = pd.read_sql(sql, MOTOR_ORIGEN)
    min_f = df["min_fecha"].iloc[0]
    max_f = df["max_fecha"].iloc[0]
    return str(min_f), str(max_f)


def ejecutar_etl_completo():
    """Ejecuta el pipeline ETL completo en el orden correcto."""
    try:
        logger.info("🚀 INICIO DEL PIPELINE ETL - Fast and Safe")
        logger.info("=" * 60)

        # 1. Determinar rango de fechas
        fecha_min, fecha_max = obtener_rango_fechas()
        logger.info(f"Rango de fechas detectado: {fecha_min} a {fecha_max}")

        # 2. Cargar dimensiones (en orden de independencia)
        logger.info("\n📊 CARGANDO DIMENSIONES")
        logger.info("-" * 60)

        dim_tiempo.ejecutar_dim_tiempo(fecha_min, fecha_max)
        dim_cliente.ejecutar_dim_cliente()
        dim_ciudad.ejecutar_dim_ciudad()
        dim_sede.ejecutar_dim_sede()
        dim_mensajero.ejecutar_dim_mensajero()
        dim_tipo_entrega.ejecutar_dim_tipo_entrega()
        dim_novedad.ejecutar_dim_novedad()
        dim_tipo_vehiculo.ejecutar_dim_tipo_vehiculo()  # NUEVA

        # 3. Cargar hechos (al final, depende de todas las dimensiones)
        logger.info("\n📈 CARGANDO HECHOS")
        logger.info("-" * 60)

        fact_servicios.ejecutar_fact_servicios()

        logger.info("=" * 60)
        logger.info("🎉 PIPELINE ETL FINALIZADO CON ÉXITO")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ FALLÓ EL PIPELINE ETL: {e}")
        raise


if __name__ == "__main__":
    ejecutar_etl_completo()