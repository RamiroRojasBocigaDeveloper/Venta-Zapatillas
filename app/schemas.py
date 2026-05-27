from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ClienteCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    telefono: str = Field(..., min_length=1, max_length=50)
    direccion: Optional[str] = Field(None, max_length=300)


class ProductoCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    marca: str = Field(..., min_length=1, max_length=100)
    referencia: str = Field(..., min_length=1, max_length=100)
    precio_compra: Decimal = Field(..., ge=0, decimal_places=0)
    precio: Decimal = Field(..., gt=0, decimal_places=0)


class VentaCreate(BaseModel):
    cliente_id: int = Field(..., gt=0)
    fecha: date
    total: Decimal = Field(..., gt=0, decimal_places=0)
    num_cuotas: int = Field(..., gt=0)
    frecuencia: str = Field(..., pattern="^(quincenal|mensual)$")
    notas: Optional[str] = Field(None)


class ReprogramarCuota(BaseModel):
    nueva_fecha: date

    @field_validator("nueva_fecha")
    @classmethod
    def fecha_no_pasada(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("La nueva fecha no puede ser anterior a hoy")
        return v
