import pytest
from pydantic import ValidationError
from schemas.user import UsuarioSchema

# ==============================================================================
# TESTES DE VALIDAÇÃO DE ACEITE DOS TERMOS (LGPD)
# ==============================================================================

def test_aceite_termos_sucesso(dados_usuario_validos):
    """Garante que a validação passa com sucesso quando aceitou_termos é True."""
    payload = dados_usuario_validos.copy()
    payload['aceitou_termos'] = True

    # Instancia o Schema do Pydantic
    schema = UsuarioSchema(**payload)

    assert schema.aceitou_termos is True


def test_aceite_termos_recusado_deve_falhar(dados_usuario_validos):
    """Garante que lançará ValidationError caso o usuário passe False."""
    payload = dados_usuario_validos.copy()
    payload['aceitou_termos'] = False

    with pytest.raises(ValidationError) as exc_info:
        UsuarioSchema(**payload)

    erros = exc_info.value.errors()
    assert len(erros) == 1
    assert (
        'Você deve aceitar os Termos de Uso e a Política de Privacidade para criar uma conta.'
        in erros[0]['msg']
    )


def test_aceite_termos_ausente_ou_tipo_invalido(dados_usuario_validos):
    """Valida o comportamento quando o campo é omitido ou enviado com tipo incorreto."""
    payload = dados_usuario_validos.copy()

    # 1. Campo omitido (rejeição por campo obrigatório)
    if 'aceitou_termos' in payload:
        del payload['aceitou_termos']

    with pytest.raises(ValidationError):
        UsuarioSchema(**payload)

    # 2. Tipo inválido (string que não é booleana convertível)
    payload['aceitou_termos'] = 'nao'

    with pytest.raises(ValidationError):
        UsuarioSchema(**payload)


def test_schema_usuario_valido(dados_usuario_validos):
    """Garante que dados válidos passam no schema sem exceção."""
    schema = UsuarioSchema(**dados_usuario_validos)
    assert schema.nome == "Carlos Eduardo"
    assert schema.email == "carlos@exemplo.com"


@pytest.mark.parametrize("nome_invalido", [
    "Carlos",              # Sem sobrenome
    "",                    # Vazio
    "Carlos123 Silva",     # Com números
    "  ",                  # Apenas espaços
])
def test_schema_nome_invalido(dados_usuario_validos, nome_invalido):
    dados = dados_usuario_validos.copy()
    dados["nome"] = nome_invalido
    with pytest.raises(ValidationError):
        UsuarioSchema(**dados)


@pytest.mark.parametrize("email_invalido", [
    "email_sem_arroba.com",
    "@dominio.com",
    "usuario@",
    "string_qualquer"
])
def test_schema_email_invalido(dados_usuario_validos, email_invalido):
    dados = dados_usuario_validos.copy()
    dados["email"] = email_invalido
    with pytest.raises(ValidationError):
        UsuarioSchema(**dados)




def test_cadastro_senha_valida_com_sucesso(client, dados_usuario_validos):
  """Garante que uma senha forte dentro dos padrões é aceita."""
  dados = dados_usuario_validos.copy()
  dados['email'] = 'senhaforte123@exemplo.com'
  dados['senha'] = 'senhaSegura123!@'

  response = client.post('/api/auth/register', json=dados)
  assert response.status_code == 201




@pytest.mark.parametrize(
    'senha_invalida, mensagem_esperada',
    [
        (
            'Curta1!',
            'senha: A senha deve conter no mínimo 8 caracteres.',
        ),
        (
            'senhasemmaiuscula1!',
            'senha: A senha deve conter pelo menos uma letra maiúscula.',
        ),
        (
            'SENHASEMMINUSCULA1!',
            'senha: A senha deve conter pelo menos uma letra minúscula.',
        ),
        (
            'SenhaSemNumero!',
            'senha: A senha deve conter pelo menos um número.',
        ),
        (
            'SenhaSemEspecial123',
            'senha:'
            ' A senha deve conter pelo menos um caractere especial (!@#$%^&* etc.).',
        ),
    ],
)

def test_cadastro_senhas_invalidas_falham(client, dados_usuario_validos, senha_invalida, mensagem_esperada):
  """Testa individualmente cada regra de complexidade de senha usando parametrização."""
  dados = dados_usuario_validos.copy()
  dados['email'] = f'teste_{hash(senha_invalida)}@exemplo.com'
  dados['senha'] = senha_invalida

  response = client.post('/api/auth/register', json=dados)
  json_data = response.get_json()

  assert response.status_code == 400
  assert 'erros' in json_data
  assert mensagem_esperada in json_data['erros']