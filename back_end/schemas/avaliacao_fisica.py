from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from models import SexoBiologico, NivelAtividade

class AvaliacaoCreateSchema(BaseModel):
    peso: float = Field(..., gt=20.0, lt=350.0, description='Peso em kg (entre 20 e 350kg)')
    altura: float = Field(..., gt=0.5, lt=2.5, description='Altura em metros (ex: 1.75)')

    nivel_atividade_padrao: NivelAtividade
    sexo_biologico: SexoBiologico  
    
    cintura: Optional[float] = Field(None, gt=30.0, lt=250.0)
    quadril: Optional[float] = Field(None, gt=30.0, lt=250.0)
    braco_relaxado: Optional[float] = Field(None, gt=10.0, lt=80.0)
    braco_contraido: Optional[float] = Field(None, gt=10.0, lt=80.0)
    
    model_config = ConfigDict(extra='forbid', use_enum_values=True)


class AvaliacaoUpdateSchema(BaseModel):
    """Schema para atualização parcial de Avaliação Física."""
    peso: Optional[float] = Field(None, gt=20.0, lt=350.0)
    altura: Optional[float] = Field(None, gt=0.5, lt=2.5)

    nivel_atividade_padrao: Optional[NivelAtividade] = None
    sexo_biologico: Optional[SexoBiologico] = None

    cintura: Optional[float] = Field(None, gt=30.0, lt=250.0)
    quadril: Optional[float] = Field(None, gt=30.0, lt=250.0)
    braco_relaxado: Optional[float] = Field(None, gt=10.0, lt=80.0)
    braco_contraido: Optional[float] = Field(None, gt=10.0, lt=80.0)

    model_config = ConfigDict(extra='forbid', use_enum_values=True)