from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from models import Objetivo

class MetaCreateSchema(BaseModel):
    """Schema para criação de uma nova Meta.
    Calorias e água são calculadas automaticamente pelo Service.
    """
    objetivo: Objetivo
    peso_alvo_kg: float = Field(
        ..., gt=20.0, lt=400.0, description='Peso desejado em kg (entre 20 e 400kg)'
    )

    model_config = ConfigDict(extra='forbid')


class MetaUpdateSchema(BaseModel):
    """Schema para atualização de Meta existente."""
    objetivo: Optional[Objetivo] = None
    peso_alvo_kg: Optional[float] = Field(
        None, gt=20.0, lt=400.0, description='Peso desejado em kg'
    )
    
    model_config = ConfigDict(extra='forbid')