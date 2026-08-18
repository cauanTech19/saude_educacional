import pytest
from datetime import date, timedelta
from pydantic import ValidationError
from schemas.user import UsuarioSchema


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

  print("\n[DEBUG RESPOSTA ERRO]:", response.get_json())

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
  assert 'erro' in json_data
  assert mensagem_esperada in json_data['erro']