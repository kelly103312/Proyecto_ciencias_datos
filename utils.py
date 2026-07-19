"""
utils.py
========
Funciones auxiliares reutilizables: logging, creación de motores SQLAlchemy.
"""
import logging
import sys
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from config import DB_ORIGEN, DB_BODEGA


def get_logger(nombre: str, nivel: int = logging.INFO) -> logging.Logger:
    """
    Crea y retorna un logger con formato consistente.

    Args:
        nombre: Nombre del logger (usualmente __name__).
        nivel: Nivel de logging (DEBUG, INFO, WARNING, ERROR).

    Returns:
        Logger configurado con handler a consola.
    """
    logger = logging.getLogger(nombre)
    logger.setLevel(nivel)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(nivel)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def normalizar_prioridad(valor) -> str:
    """
    Normaliza el texto libre de `mensajeria_servicio.prioridad` a un valor canónico
    (Alta/Media/Baja), colapsando variantes de redacción como
    "Alta: En una Hora" / "Alta: En una hora" al mismo valor "Alta".
    Se usa tanto en dim_tipo_entrega.py como en fact_servicios.py para que el
    mapeo entre ambos coincida siempre.
    """
    if valor is None or valor != valor:  # valor != valor detecta NaN sin depender de pandas
        return "Desconocido"
    etiqueta = str(valor).split(":")[0].strip()
    return etiqueta if etiqueta else "Desconocido"


def crear_motor(db_config: dict) -> Engine:
    """
    Crea un motor SQLAlchemy a partir de un diccionario de configuración.

    Args:
        db_config: Diccionario con host, port, database, user, password.

    Returns:
        Engine de SQLAlchemy listo para ejecutar queries.
    """
    url = (
        f"postgresql+psycopg2://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )
    return create_engine(url)


# Motores globales (singleton por módulo)
MOTOR_ORIGEN = crear_motor(DB_ORIGEN)
MOTOR_BODEGA = crear_motor(DB_BODEGA)