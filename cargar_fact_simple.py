"""
cargar_fact_simple.py
Script independiente para cargar fact_servicios sin complicaciones.
"""
import pandas as pd
from sqlalchemy import text
from hechos.fact_servicios import extraer, transformar, _construir_mapeos_sk, DDL_FACT_SERVICIOS
from utils import MOTOR_BODEGA, get_logger

logger = get_logger("CARGA_SIMPLE")


def cargar_simple():
    logger.info("=" * 60)
    logger.info("CARGA SIMPLE DE FACT_SERVICIOS")
    logger.info("=" * 60)
    
    # 1. Extraer y transformar
    logger.info("\n📥 Extrayendo y transformando...")
    datos = extraer()
    mapeos = _construir_mapeos_sk(MOTOR_BODEGA)
    fact = transformar(datos, mapeos)
    
    # 2. Crear tabla
    logger.info("\n🏗️  Creando tabla...")
    with MOTOR_BODEGA.begin() as conn:
        conn.execute(text(DDL_FACT_SERVICIOS))
    logger.info("  ✅ Tabla creada")
    
    # 3. Cargar usando SQL puro (método infalible)
    logger.info("\n📤 Cargando con INSERT SQL puro...")
    
    columnas = ", ".join(fact.columns)
    placeholders = ", ".join([f":{col}" for col in fact.columns])
    insert_sql = f"INSERT INTO fact_servicios ({columnas}) VALUES ({placeholders})"
    
    # Convertir DataFrame a lista de diccionarios
    registros = fact.to_dict(orient='records')
    
    # Ejecutar en lotes de 500
    lote_size = 500
    total = len(registros)
    
    with MOTOR_BODEGA.begin() as conn:
        for i in range(0, total, lote_size):
            lote = registros[i:i + lote_size]
            conn.execute(text(insert_sql), lote)
            logger.info(f"  ✅ Lote {i//lote_size + 1}: {min(i+lote_size, total)}/{total} filas")
    
    logger.info(f"\n✅ {total} filas cargadas exitosamente")
    
    # 4. Verificar
    df_count = pd.read_sql("SELECT COUNT(*) AS total FROM fact_servicios", MOTOR_BODEGA)
    logger.info(f"📊 Verificación: {df_count['total'].iloc[0]} filas en la bodega")


if __name__ == "__main__":
    cargar_simple()