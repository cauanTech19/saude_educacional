from enum import Enum
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, field_validator

from rotas.formatadores import formatar_erros_pydantic


# --- SCHEMAS DUMMY PARA OS TESTES ---
class OpcoesEnum(str, Enum):
    OPCAO_A = "A"
    OPCAO_B = "B"


class SchemaCompletoTestes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str = Field(min_length=1)
    email: EmailStr
    opcao: OpcoesEnum
    valor_float: float = Field(gt=0)
    valor_int: int = Field(le=100)


class SchemaComValidatorCustomizado(BaseModel):
    campo: str

    @field_validator("campo")
    @classmethod
    def validar_campo(cls, v: str) -> str:
        raise ValueError("O nome informado é inválido.")


# --- TESTES UNITÁRIOS DA FUNÇÃO ---


def test_email_invalido():
    """Valida bloco 1: regra de e-mail."""
    try:
        SchemaCompletoTestes(
            texto="Ok",
            email="email_invalido",
            opcao=OpcoesEnum.OPCAO_A,
            valor_float=10.0,
            valor_int=10,
        )
    except ValidationError as e:
        erros = formatar_erros_pydantic(e)
        assert (
            "email: Informe um e-mail válido (ex: nome@dominio.com)." in erros
        )


def test_campo_extra_proibido():
    """Valida bloco 1 (extra_forbidden): quando o schema bloqueia atributos extras."""
    try:
        SchemaCompletoTestes(
            texto="Ok",
            email="test@email.com",
            opcao=OpcoesEnum.OPCAO_A,
            valor_float=10.0,
            valor_int=10,
            campo_desconhecido="invalido",
        )
    except ValidationError as e:
        erros = formatar_erros_pydantic(e)
        assert (
            "campo_desconhecido: O campo 'campo_desconhecido' não é permitido nesta requisição."
            in erros
        )


def test_tipos_numericos_ou_invalidos():
    """Valida bloco 2: envio de None/tipos incorretos em campos numéricos."""
    try:
        SchemaCompletoTestes(
            texto="Ok",
            email="test@email.com",
            opcao=OpcoesEnum.OPCAO_A,
            valor_float=None,
            valor_int="texto_no_lugar_de_int",
        )
    except ValidationError as e:
        erros = formatar_erros_pydantic(e)
        assert "valor_float: Este campo não pode ser nulo." in erros
        assert "valor_int: Este campo não pode ser nulo." in erros


def test_limites_minimos_e_maximos():
    """Valida blocos 3 e 4: limites gt/ge (maior que) e lt/le (menor que)."""
    try:
        SchemaCompletoTestes(
            texto="Ok",
            email="test@email.com",
            opcao=OpcoesEnum.OPCAO_A,
            valor_float=-5.0,  # Precisa ser > 0
            valor_int=150,  # Precisa ser <= 100
        )
    except ValidationError as e:
        erros = formatar_erros_pydantic(e)
        assert "valor_float: O valor deve ser maior que 0.0." in erros
        assert "valor_int: O valor deve ser menor que 100." in erros


def test_dicionario_traducoes_missing_e_enum():
    """Valida dicionário TRADUCOES: campos obrigatórios ausentes e enum inválido."""
    try:
        SchemaCompletoTestes(opcao="OPCAO_INEXISTENTE")
    except ValidationError as e:
        erros = formatar_erros_pydantic(e)
        assert "texto: Este campo é obrigatório." in erros
        assert "email: Este campo é obrigatório." in erros
        assert "opcao: Opção inválida selecionada." in erros


def test_remover_prefixo_value_error():
    """Valida bloco 5: remoção da string 'Value error, ' vinda de @field_validator."""
    try:
        SchemaComValidatorCustomizado(campo="qualquer_valor")
    except ValidationError as e:
        erros = formatar_erros_pydantic(e)
        assert "campo: O nome informado é inválido." in erros