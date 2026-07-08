"""
dimensiones/__init__.py
=======================
Paquete que contiene todas las dimensiones del modelo estrella.
Cada módulo expone una función `ejecutar_dim_*()` que ejecuta el pipeline completo
de su dimensión (Extract -> Transform -> Load).
"""

from . import (
    dim_tiempo,
    dim_cliente,
    dim_ciudad,
    dim_sede,
    dim_mensajero,
    dim_tipo_entrega,
    dim_novedad,
    dim_tipo_vehiculo,  # NUEVA
)

__all__ = [
    "dim_tiempo",
    "dim_cliente",
    "dim_ciudad",
    "dim_sede",
    "dim_mensajero",
    "dim_tipo_entrega",
    "dim_novedad",
    "dim_tipo_vehiculo",
]