"""
hechos/__init__.py
===================
Paquete que contiene las tablas de hechos del modelo estrella.
Cada módulo expone una función `ejecutar_fact_*()` que ejecuta el pipeline
completo de su hecho (Extract -> Transform -> Load).
"""

from . import (
    fact_servicios,
    fact_novedades,  # NUEVA (A2)
)

__all__ = [
    "fact_servicios",
    "fact_novedades",
]
