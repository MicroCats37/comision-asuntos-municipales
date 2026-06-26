"""
Domain schemas — DTOs internos para Ingeniero/Habilitación CIP.
"""
import uuid
from datetime import datetime, date
from pydantic import BaseModel, Field
from typing import Optional


class CapituloData(BaseModel):
    """Datos del capítulo profesional."""
    id: str
    descripcion: Optional[str] = None
    abreviatura: Optional[str] = None
    grupoEnviosInst: Optional[str] = None


class CipColegiadoData(BaseModel):
    """
    DTO con datos crudos del endpoint CIP.

    Mapea los campos del response externo:
    - cip, paterno, materno, nombre1, nombre2, dni, fechaNacimiento
    - codGenero, celular, correoPers, correoInst, direccion, distritoId
    - codCapitulo, codEspecialidad, codConsejo, condicion, ultimoPeriodoPagado
    - capitulo (objeto nested)
    """
    cip: str
    paterno: str
    materno: str
    nombre1: str
    nombre2: Optional[str] = ""
    dni: str
    fechaNacimiento: Optional[str] = None
    codGenero: Optional[str] = None
    celular: Optional[str] = None
    correoPers: Optional[str] = None
    correoInst: Optional[str] = None
    direccion: Optional[str] = None
    distritoId: Optional[str] = None
    codCapitulo: Optional[str] = None
    codEspecialidad: Optional[str] = None
    codConsejo: Optional[str] = None
    condicion: str = Field(description="Condición CIP (1 = habilitado, 0 = no habilitado)")
    ultimoPeriodoPagado: Optional[str] = None
    capitulo: Optional[CapituloData] = None

    @property
    def habilitado(self) -> bool:
        """Computado: el ingeniero está habilitado si condicion == '1'."""
        return self.condicion == "1"

    @property
    def nombres_completo(self) -> str:
        """Construye el nombre completo."""
        parts = [p for p in [self.nombre1, self.nombre2] if p]
        return " ".join(parts)

    @property
    def apellidos_completo(self) -> str:
        """Construye los apellidos completos."""
        return f"{self.paterno} {self.materno}".strip()


class IngenieroHabilitadoResult(BaseModel):
    """
    DTO de resultado para el caso de uso de obtener ingeniero habilitado.

    Incluye todos los datos del colegiado más el flag habilitado calculado.
    """
    cip: str
    paterno: str
    materno: str
    nombre1: str
    nombre2: Optional[str] = ""
    dni: str
    fechaNacimiento: Optional[date] = None
    codGenero: Optional[str] = None
    celular: Optional[str] = None
    correoPers: Optional[str] = None
    correoInst: Optional[str] = None
    direccion: Optional[str] = None
    distritoId: Optional[str] = None
    codCapitulo: Optional[str] = None
    codEspecialidad: Optional[str] = None
    codConsejo: Optional[str] = None
    condicion: str
    ultimoPeriodoPagado: Optional[str] = None
    capitulo: Optional[CapituloData] = None
    habilitado: bool = Field(description="True si condicion == '1'")

    @classmethod
    def from_cip_data(cls, data: CipColegiadoData) -> "IngenieroHabilitadoResult":
        """Factory para crear desde CipColegiadoData."""
        # Parse fechaNacimiento si está disponible
        fecha_nac = None
        if data.fechaNacimiento:
            try:
                fecha_nac = datetime.strptime(data.fechaNacimiento, "%Y-%m-%d").date()
            except ValueError:
                pass

        return cls(
            cip=data.cip,
            paterno=data.paterno,
            materno=data.materno,
            nombre1=data.nombre1,
            nombre2=data.nombre2,
            dni=data.dni,
            fechaNacimiento=fecha_nac,
            codGenero=data.codGenero,
            celular=data.celular,
            correoPers=data.correoPers,
            correoInst=data.correoInst,
            direccion=data.direccion,
            distritoId=data.distritoId,
            codCapitulo=data.codCapitulo,
            codEspecialidad=data.codEspecialidad,
            codConsejo=data.codConsejo,
            condicion=data.condicion,
            ultimoPeriodoPagado=data.ultimoPeriodoPagado,
            capitulo=data.capitulo,
            habilitado=data.habilitado,
        )
