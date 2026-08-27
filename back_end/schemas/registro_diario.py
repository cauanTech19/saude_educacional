from typing import Optional
from pydantic import BaseModel, Field

class RegistroDiarioBase(BaseModel):
    calorias_consumidas_kcal: Optional[float] = Field(
        default=None, ge=0.0, le=15000.0, description="Calorias totais (0 a 15.000 kcal)"
    )
    proteinas_g: Optional[float] = Field(
        default=None, ge=0.0, le=600.0, description="Proteínas em gramas (0 a 600g)"
    )
    carboidratos_g: Optional[float] = Field(
        default=None, ge=0.0, le=1500.0, description="Carboidratos em gramas (0 a 1.500g)"
    )
    gorduras_g: Optional[float] = Field(
        default=None, ge=0.0, le=500.0, description="Gorduras em gramas (0 a 500g)"
    )
    agua_consumida_ml: Optional[float] = Field(
        default=None, ge=0.0, le=10000.0, description="Água em mL (0 a 10.000ml)"
    )
    exercicio_realizado: Optional[bool] = Field(
        default=None, description="Indica se realizou atividade física no dia"
    )
    peso_registro_kg: Optional[float] = Field(
        default=None, ge=20.0, le=350.0, description="Peso em kg (20kg a 350kg)"
    )
    observacoes: Optional[str] = Field(
        default=None, max_length=255, description="Anotações gerais do dia"
    )


class RegistroDiarioCreateSchema(RegistroDiarioBase):
    meta_id: int = Field(
        ..., gt=0, description="ID da meta vinculada (obrigatório e imutável)"
    )


class RegistroDiarioUpdateSchema(RegistroDiarioBase):
    ...