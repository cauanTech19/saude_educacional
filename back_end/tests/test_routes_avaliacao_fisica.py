import pytest
from flask_jwt_extended import create_access_token
from models import StatusAvaliacaoEnum


@pytest.fixture
def auth_headers(app, usuario_db):
    """Gera o cabeçalho Authorization com JWT token válido para o usuário de teste."""
    with app.app_context():
        token = create_access_token(identity=str(usuario_db.id))
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }


@pytest.fixture
def payload_valido():
    return {
        "peso": 75.0,
        "altura": 1.75,
        "sexo_biologico": "M",
        "nivel_atividade_padrao": "leve",  # Uppercase para coincidir com o Enum
        "cintura": 80.0,
        "quadril": 95.0,
        "braco_relaxado": 32.0,
        "braco_contraido": 35.0
    }


# ==============================================================================
# 1. CRIAR AVALIAÇÃO (POST)
# ==============================================================================
def test_criar_avaliacao_sucesso(client, auth_headers, payload_valido):
    response = client.post('/api/avaliacoes/', json=payload_valido, headers=auth_headers)
    
    # Passa o JSON retornado como mensagem da asserção
    assert response.status_code == 201, f"Erro retornado pela API: {response.get_json()}"
def test_criar_avaliacao_sem_autenticacao(client, payload_valido):
    response = client.post('/api/avaliacoes/', json=payload_valido)
    assert response.status_code == 401


def test_criar_avaliacao_payload_invalido_pydantic(client, auth_headers):
    # Peso inválido (10.0), mas com TODOS os campos obrigatórios presentes e válidos
    payload = {
        'peso': 10.0, 
        'altura': 1.75,
        'sexo_biologico': 'MASCULINO',
        'nivel_atividade_padrao': 'MODERADO'
    }
    response = client.post('/api/avaliacoes/', json=payload, headers=auth_headers)
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['erro'] == 'Dados inválidos na requisição'
    assert 'detalhes' in data


# ==============================================================================
# 2. LISTAR AVALIAÇÕES (GET)
# ==============================================================================
def test_listar_avaliacoes_usuario(client, auth_headers, payload_valido):
    client.post('/api/avaliacoes/', json=payload_valido, headers=auth_headers)

    response = client.get('/api/avaliacoes/', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['total'] >= 1
    assert isinstance(data['dados'], list)


# ==============================================================================
# 3. ATUALIZAR AVALIAÇÃO (PUT)
# ==============================================================================
def test_atualizar_avaliacao_sucesso(client, auth_headers, payload_valido):
    res_post = client.post('/api/avaliacoes/', json=payload_valido, headers=auth_headers)
    avaliacao_id = res_post.get_json()['dados']['id']

    update_payload = payload_valido.copy()
    update_payload['peso'] = 80.0

    response = client.put(f'/api/avaliacoes/{avaliacao_id}', json=update_payload, headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['dados']['peso'] == 80.0


def test_atualizar_avaliacao_nao_encontrada(client, auth_headers, payload_valido):
    response = client.put('/api/avaliacoes/99999', json=payload_valido, headers=auth_headers)
    assert response.status_code == 404


# ==============================================================================
# 4. DESATIVAR E REATIVAR AVALIAÇÃO (DELETE & PUT REATIVAR)
# ==============================================================================
def test_fluxo_desativar_e_reativar_avaliacao(client, auth_headers, payload_valido):
    # 1. Cria
    res_post = client.post('/api/avaliacoes/', json=payload_valido, headers=auth_headers)
    avaliacao_id = res_post.get_json()['dados']['id']

    # 2. Desativa (Soft Delete)
    res_del = client.delete(f'/api/avaliacoes/{avaliacao_id}', headers=auth_headers)
    assert res_del.status_code == 200

    # 3. Tenta listar (não deve vir por padrão pois ativas=true)
    res_list = client.get('/api/avaliacoes/', headers=auth_headers)
    ids_ativos = [a['id'] for a in res_list.get_json()['dados']]
    assert avaliacao_id not in ids_ativos

    # 4. Reativa
    res_react = client.put(f'/api/avaliacoes/{avaliacao_id}/reativar', headers=auth_headers)
    assert res_react.status_code == 200
    assert res_react.get_json()['dados']['ativo'] == StatusAvaliacaoEnum.ATIVO


def test_criar_avaliacao_campo_extra_proibido(client, auth_headers, payload_valido):
    payload_com_extra = payload_valido.copy()
    payload_com_extra['campo_inventado'] = 'valor_invalido'

    response = client.post(
        '/api/avaliacoes/', json=payload_com_extra, headers=auth_headers
    )

    assert response.status_code == 400
    data = response.get_json()

    assert data['erro'] in ('Dados inválidos', 'Dados inválidos na requisição')
    detalhes = data['detalhes']
    assert isinstance(detalhes, list)
    assert any("campo_inventado" in str(msg) for msg in detalhes)