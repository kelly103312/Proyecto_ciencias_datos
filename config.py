"""
config.py
=========
Configuración centralizada de conexiones y constantes del proyecto ETL.
Para producción, usa variables de entorno desde un archivo .env.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Conexión a la BD OPERACIONAL (origen - PostgreSQL/Django)
# ============================================================
DB_ORIGEN = {
    "host": os.getenv("DB_ORIGEN_HOST", "localhost"),
    "port": os.getenv("DB_ORIGEN_PORT", "5432"),
    "database": os.getenv("DB_ORIGEN_NAME", "fast_and_safe_ops"),
    "user": os.getenv("DB_ORIGEN_USER", "postgres"),
    "password": os.getenv("DB_ORIGEN_PASSWORD", ""),
}

# ============================================================
# Conexión a la BODEGA DE DATOS (destino - PostgreSQL)
# ============================================================
DB_BODEGA = {
    "host": os.getenv("DB_BODEGA_HOST", "localhost"),
    "port": os.getenv("DB_BODEGA_PORT", "5432"),
    "database": os.getenv("DB_BODEGA_NAME", "fast_and_safe_dw"),
    "user": os.getenv("DB_BODEGA_USER", "postgres"),
    "password": os.getenv("DB_BODEGA_PASSWORD", ""),
}

# ============================================================
# Esquema y constantes del negocio
# ============================================================
ESQUEMA_BODEGA = "public"

# Estados del servicio (usado para pivotear la tabla de estados)
ESTADOS_SERVICIO = [
    "Iniciado",
    "Con mensajero asignado",
    "Recogido en origen",
    "Entregado en Destino",
    "Cerrado",
]

# Festivos de Colombia 2025-2026 (Ley Emiliani)
FESTIVOS_COLOMBIA = {
    "2025-01-01": "Año Nuevo",
    "2025-01-06": "Reyes Magos",
    "2025-03-24": "San José",
    "2025-04-17": "Jueves Santo",
    "2025-04-18": "Viernes Santo",
    "2025-05-01": "Día del Trabajo",
    "2025-06-02": "Ascensión del Señor",
    "2025-06-23": "Corpus Christi",
    "2025-06-30": "Sagrado Corazón",
    "2025-07-01": "San Pedro y San Pablo",
    "2025-07-20": "Grito de Independencia",
    "2025-08-07": "Batalla de Boyacá",
    "2025-08-18": "Asunción de la Virgen",
    "2025-10-13": "Día de la Raza",
    "2025-11-03": "Todos los Santos",
    "2025-11-17": "Independencia de Cartagena",
    "2025-12-08": "Inmaculada Concepción",
    "2025-12-25": "Navidad",
    "2026-01-01": "Año Nuevo",
    "2026-01-12": "Reyes Magos",
    "2026-03-23": "San José",
    "2026-04-02": "Jueves Santo",
    "2026-04-03": "Viernes Santo",
    "2026-05-01": "Día del Trabajo",
    "2026-05-18": "Ascensión del Señor",
    "2026-06-08": "Corpus Christi",
    "2026-06-15": "Sagrado Corazón",
    "2026-06-29": "San Pedro y San Pablo",
    "2026-07-04": "Día de la Independencia (trasladado)",
    "2026-07-20": "Grito de Independencia",
    "2026-08-07": "Batalla de Boyacá",
    "2026-08-17": "Asunción de la Virgen",
    "2026-10-12": "Día de la Raza",
    "2026-11-02": "Todos los Santos",
    "2026-11-16": "Independencia de Cartagena",
    "2026-12-08": "Inmaculada Concepción",
    "2026-12-25": "Navidad",
}