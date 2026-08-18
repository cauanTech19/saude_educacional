import pytest
from pydantic import ValidationError
from schemas.avaliacao_fisica import AvaliacaoCreateSchema
from rotas.formatadores import formatar_erros_pydantic  

def test_schema_avaliacao_sucesso():
  """Testa a criação do schema com dados válidos completos e mínimos."""
  # Dados completos válidos
  dados_completos = {
        "peso": 75.0,
        "altura": 1.75,
        "sexo_biologico": "M",
        "nivel_atividade_padrao": "leve",  # Uppercase para coincidir com o Enum
        "cintura": 80.0,
        "quadril": 95.0,
        "braco_relaxado": 32.0,
        "braco_contraido": 35.0
    }

  schema = AvaliacaoCreateSchema(**dados_completos)
  assert schema.peso == 75.0
  assert schema.altura == 1.75

  # Dados apenas obrigatórios
  dados_minimos = {"peso": 60.0, "altura": 1.65, "sexo_biologico": 'M', "nivel_atividade_padrao": "leve",
}
  schema_minimo = AvaliacaoCreateSchema(**dados_minimos)
  assert schema_minimo.peso == 60.0


def test_schema_avaliacao_campos_obrigatorios_ausentes():
  """Testa se o schema falha e formata os erros quando faltam campos obrigatórios."""
  with pytest.raises(ValidationError) as exc_info:
    AvaliacaoCreateSchema(**{})

  erros = formatar_erros_pydantic(exc_info.value)

  assert "peso: Este campo é obrigatório." in erros
  assert "altura: Este campo é obrigatório." in erros


def test_schema_avaliacao_limite_peso_invalido():
  """Testa validação de peso abaixo do mínimo (gt=20.0) e acima do máximo (lt=350.0)."""
  # Peso menor que 20kg
  with pytest.raises(ValidationError) as exc_info_baixo:
    AvaliacaoCreateSchema(peso=15.0, altura=1.70, idade=20)

  erros_baixo = formatar_erros_pydantic(exc_info_baixo.value)
  assert "peso: O valor deve ser maior que 20.0." in erros_baixo

  # Peso maior que 350kg
  with pytest.raises(ValidationError) as exc_info_alto:
    AvaliacaoCreateSchema(peso=400.0, altura=1.70, idade=20)

  erros_alto = formatar_erros_pydantic(exc_info_alto.value)
  assert "peso: O valor deve ser menor que 350.0." in erros_alto


def test_schema_avaliacao_limite_altura_invalida():
  """Testa validação de altura fora dos limites (gt=0.5 e lt=2.5)."""
  with pytest.raises(ValidationError) as exc_info:
    AvaliacaoCreateSchema(peso=70.0, altura=0.3, idade=20)

  erros = formatar_erros_pydantic(exc_info.value)
  assert "altura: O valor deve ser maior que 0.5." in erros


def test_schema_avaliacao_campo_nulo_invalido():
  """Testa o comportamento quando um campo obrigatório é passado como None."""
  with pytest.raises(ValidationError) as exc_info:
    AvaliacaoCreateSchema(peso=None, altura=1.75, idade=20)

  erros = formatar_erros_pydantic(exc_info.value)
  assert "peso: Este campo não pode ser nulo." in erros