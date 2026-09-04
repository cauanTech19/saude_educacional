import re
from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from pydantic_core import PydanticCustomError

class UsuarioSchema(BaseModel):
  """Schema único para validação de dados de Usuário."""

  nome: str = Field(..., min_length=3, max_length=100)
  email: EmailStr
  senha: str 
  data_nascimento: date
  model_config = ConfigDict(extra='forbid')
  aceitou_termos: bool

  @field_validator('aceitou_termos')
  @classmethod
  def validar_aceite(cls, valor: bool) -> bool:
    if not valor:
      raise ValueError(
        'Você deve aceitar os Termos de Uso e a Política de Privacidade para criar uma conta.'
      )
    return valor


  @field_validator("nome")
  @classmethod
  def validar_nome_completo(cls, usuario: str) -> str:
    usuario = usuario.strip()
    
    if not usuario:
      raise ValueError("O nome não pode estar vazio.")

    nome_completo = usuario.split()

    if len(nome_completo) < 2:
      raise PydanticCustomError(
        'value_error', 'O nome deve conter pelo menos nome e sobrenome.'
      )
    
    if not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s]+$", usuario):
      raise PydanticCustomError(
        'value_error', 'O nome deve conter apenas letras.'
      )
    
    return usuario.title()
  
  @field_validator('senha')
  @classmethod
  def validar_senha_forte(cls, senha: str) -> str:
    # 1. Tamanho mínimo de 8 caracteres
    if len(senha) < 8:
      raise PydanticCustomError(
        'value_error', 
        'A senha deve conter no mínimo 8 caracteres.'
      )
        
    # 2. Pelo menos uma letra maiúscula
    if not re.search(r'[A-Z]', senha):
        raise PydanticCustomError(
          'value_error', 
          'A senha deve conter pelo menos uma letra maiúscula.'
        )
            
    # 3. Pelo menos uma letra minúscula
    if not re.search(r'[a-z]', senha):
      raise PydanticCustomError(
          'value_error', 
          'A senha deve conter pelo menos uma letra minúscula.'
        )
            
    # 4. Pelo menos um número
    if not re.search(r'[0-9]', senha):
        raise PydanticCustomError(
        'value_error', 
        'A senha deve conter pelo menos um número.'
      )
            
    # 5. Pelo menos um caractere especial (!@#$%^&* etc.)
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', senha):
        raise PydanticCustomError(
        'value_error', 
        'A senha deve conter pelo menos um caractere especial (!@#$%^&* etc.).'
      )

    return senha


class UsuarioLoginSchema(BaseModel):
  email: EmailStr
  senha: str
  model_config = ConfigDict(extra='forbid')
 
  


class UsuarioUpdateSchema(BaseModel):
    """Schema para atualização parcial do perfil (PUT)."""
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    senha: Optional[str] = None
    data_nascimento: Optional[date] = None
    model_config = ConfigDict(extra='forbid')

    # Reutiliza os mesmos validators chamando as funções do schema principal se o valor for passado
    @field_validator("nome")
    @classmethod
    def validar_nome(cls, nome:str):
        if nome is not None:
            return UsuarioSchema.validar_nome_completo(nome)
        return nome

    @field_validator("senha")
    @classmethod
    def validar_senha(cls, senha):
        if senha is not None:
            return UsuarioSchema.validar_senha_forte(senha)
        return senha