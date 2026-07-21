"""
diagnostico.py
==============
Script para diagnosticar el error de carga en fact_servicios.
Ejecuta solo la transformación (sin cargar a la BD) para ver el DataFrame resultante.
"""
from hechos.fact_servicios import extraer, transformar, _construir_mapeos_sk
from utils import MOTOR_BODEGA, get_logger

logger = get_logger("DIAGNOSTICO")


def diagnosticar():
    logger.info("=" * 60)
    logger.info("DIAGNÓSTICO DE FACT_SERVICIOS")
    logger.info("=" * 60)

    # 1. Extraer datos
    logger.info("\nExtrayendo datos...")
    datos = extraer()

    # 2. Construir mapeos
    logger.info("\nConstruyendo mapeos de SK...")
    mapeos = _construir_mapeos_sk(MOTOR_BODEGA)

    # 3. Transformar
    logger.info("\nTransformando datos...")
    try:
        fact = transformar(datos, mapeos)
    except Exception as e:
        logger.error(f"Error durante transformación: {e}")
        return

    # 4. Mostrar información del DataFrame
    logger.info("\nRESULTADO DEL DATAFRAME")
    logger.info("-" * 60)
    logger.info(f"Filas: {len(fact)}")
    logger.info(f"Columnas ({len(fact.columns)}):")
    for i, col in enumerate(fact.columns, 1):
        logger.info(f"  {i:2}. {col}")

    # 5. Detectar columnas problemáticas
    logger.info("\nDETECTANDO COLUMNAS SOSPECHOSAS")
    logger.info("-" * 60)
    columnas_sospechosas = [c for c in fact.columns if "_m999" in c or "_x" in c or "_y" in c]
    if columnas_sospechosas:
        logger.warning(f"Columnas con sufijos extraños: {columnas_sospechosas}")
    else:
        logger.info("No se encontraron sufijos extraños")

    # 6. Mostrar primeros registros
    logger.info("\nPRIMEROS 3 REGISTROS")
    logger.info("-" * 60)
    logger.info(fact.head(3).to_string())

    # 7. Verificar tipos de datos
    logger.info("\nTIPOS DE DATOS")
    logger.info("-" * 60)
    for col in fact.columns:
        logger.info(f"  {col:35} -> {fact[col].dtype}")

    # 8. Detectar valores None en booleanos (problema común)
    logger.info("\nVALORES NULL EN BOOLEANOS")
    logger.info("-" * 60)
    for col in ["tiene_novedad", "servicio_completado_exitosamente", "entrega_puntual"]:
        if col in fact.columns:
            nulos = fact[col].isna().sum()
            logger.info(f"  {col}: {nulos} valores NULL")

    logger.info("\n" + "=" * 60)
    logger.info("DIAGNÓSTICO COMPLETADO")
    logger.info("=" * 60)


if __name__ == "__main__":
    diagnosticar()