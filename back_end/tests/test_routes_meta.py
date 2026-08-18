from unittest.mock import patch
import json
import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from models import StatusMetaEnum, Objetivo
from rotas.rota_meta import meta_bp


# ==============================================================================
# FIXTURES E CONFIGURAÇÃO DA APLICAÇÃO DE TESTES
# ==============================================================================
@pytest.fixture
def app():
    """Cria e configura uma instância do Flask para os testes."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["JWT_SECRET_KEY"] = "chave-secreta-para-testes-pytest"

    JWTManager(app)
    app.register_blueprint(meta_bp, url_prefix="/api/metas")

    return app


@pytest.fixture
def client(app):
    """Cliente de testes do Flask."""
    return app.test_client()


@pytest.fixture
def headers_jwt_int(app):
    """Headers com Token JWT em que o identity é a string de um ID numérico ("1")."""
    with app.app_context():
        token = create_access_token(identity="1")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }


@pytest.fixture
def headers_jwt_dict(app):
    """Headers com Token JWT contendo claims adicionais simulando dicionário via additional_claims."""
    with app.app_context():
        token = create_access_token(
            identity="1",
            additional_claims={"user_data": {"id": 1}}
        )
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }


# ==============================================================================
# 1. TESTES DE AUTENTICAÇÃO E EXTRAÇÃO DE ID
# ==============================================================================
def test_obter_usuario_id_com_diferentes_payloads_jwt(client, headers_jwt_dict):
    """Garante que a extração de ID funciona com o token JWT válido."""
    with patch("services.meta_service.MetaService.obter_meta_ativa") as mock_service:
        mock_service.return_value = ({"id": 10, "objetivo": "HIPERTROFIA"}, None)

        response = client.get("/api/metas/ativa", headers=headers_jwt_dict)

        assert response.status_code == 200
        mock_service.assert_called_once_with(1)


def test_rota_protegida_sem_jwt(client):
    """Garante que requisições sem JWT retornam 401 Unauthorized."""
    response = client.get("/api/metas/ativa")
    assert response.status_code == 401


# ==============================================================================
# 2. TESTES DE CRIAR META (POST /api/metas/)
# ==============================================================================
def test_criar_meta_sucesso(client, headers_jwt_int):
    """Garante que uma meta válida é criada com sucesso (HTTP 201)."""
    payload = {"objetivo": Objetivo.MANTER, "peso_alvo_kg": 75.0}

    meta_mock = {
        "id": 1,
        "usuario_id": 1,
        "objetivo": Objetivo.MANTER,
        "peso_alvo_kg": 75.0,
        "status": StatusMetaEnum.ATIVA,
    }

    with patch("services.meta_service.MetaService.criar_meta") as mock_service:
        mock_service.return_value = (meta_mock, None)

        response = client.post("/api/metas/", json=payload, headers=headers_jwt_int)
        
        assert response.status_code == 201
        res_data = response.get_json()
        assert res_data["mensagem"] == "Meta criada com sucesso!"
        assert res_data["dados"]["id"] == 1
        mock_service.assert_called_once_with(1, payload)


def test_criar_meta_erro_pydantic_validacao(client, headers_jwt_int):
    """Garante erro HTTP 400 quando o payload falha na validação Pydantic."""
    payload = {"objetivo": "EMAGRECIMENTO", "peso_alvo_kg": 10.0}

    with patch("rotas.rota_meta.formatar_erros_pydantic") as mock_formatador:
        mock_formatador.return_value = [{"campo": "peso_alvo_kg", "erro": "Valor deve ser maior que 20"}]

        response = client.post("/api/metas/", json=payload, headers=headers_jwt_int)

        assert response.status_code == 400
        res_data = response.get_json()
        assert res_data["erro"] == "Dados inválidos na requisição"
        assert "detalhes" in res_data


def test_criar_meta_erro_regra_de_negocio_service(client, headers_jwt_int):
    """Garante erro HTTP 400 quando o Service rejeita a criação por regra de negócio."""
    payload = {"objetivo": "HIPERTROFIA", "peso_alvo_kg": 80.0}

    with patch("services.meta_service.MetaService.criar_meta") as mock_service:
        mock_service.return_value = (None, "Usuário já possui uma meta ativa.")

        response = client.post("/api/metas/", json=payload, headers=headers_jwt_int)

        assert response.status_code == 400
        res_data = response.get_json()
        assert res_data["erro"] == "Dados inválidos na requisição"


def test_criar_meta_payload_vazio(client, headers_jwt_int):
    """Garante tratamento correto caso o body da requisição venha sem JSON."""
    response = client.post(
        "/api/metas/",
        data=json.dumps({}),
        headers=headers_jwt_int
    )
    assert response.status_code == 400
    res_data = response.get_json()
    assert res_data["erro"] == "Dados inválidos na requisição"


# ==============================================================================
# 3. TESTES DE OBTER META ATIVA (GET /api/metas/ativa)
# ==============================================================================
def test_obter_meta_ativa_sucesso(client, headers_jwt_dict):
    """Garante a busca bem-sucedida da meta ativa (HTTP 200)."""
    meta_mock = {"id": 5, "objetivo": "ganhar_massa", "status": "ATIVA"}

    with patch("services.meta_service.MetaService.obter_meta_ativa") as mock_service:
        mock_service.return_value = (meta_mock, None)

        response = client.get("/api/metas/ativa", headers=headers_jwt_dict)

        assert response.status_code == 200
        res_data = response.get_json()
        assert res_data["dados"]["id"] == 5
        mock_service.assert_called_once_with(1)


def test_obter_meta_ativa_nao_encontrada(client, headers_jwt_int):
    """Garante erro HTTP 404 quando o usuário não possui meta ativa."""
    with patch("services.meta_service.MetaService.obter_meta_ativa") as mock_service:
        mock_service.return_value = (None, "Nenhuma meta ativa encontrada.")

        response = client.get("/api/metas/ativa", headers=headers_jwt_int)

        assert response.status_code == 404
        res_data = response.get_json()
        assert res_data["erro"] == "Nenhuma meta ativa encontrada."


# ==============================================================================
# 4. TESTES DE ATUALIZAR META (PUT /api/metas/<id>)
# ==============================================================================
def test_atualizar_meta_sucesso(client, headers_jwt_int):
    """Garante a atualização pontual bem-sucedida da meta (HTTP 200)."""
    payload = {"peso_alvo_kg": 72.5}
    meta_atualizada_mock = {"id": 3, "peso_alvo_kg": 72.5, "status": "ATIVA"}

    with patch("services.meta_service.MetaService.atualizar_meta") as mock_service:
        mock_service.return_value = (meta_atualizada_mock, None)

        response = client.put("/api/metas/3", json=payload, headers=headers_jwt_int)

        assert response.status_code == 200
        res_data = response.get_json()
        assert res_data["mensagem"] == "Meta atualizada com sucesso!"
        assert res_data["dados"]["peso_alvo_kg"] == 72.5
        mock_service.assert_called_once_with(meta_id=3, usuario_id=1, dados_validados=payload)


def test_atualizar_meta_erro_pydantic_validacao(client, headers_jwt_int):
    """Garante HTTP 400 ao enviar dados inválidos para atualização."""
    payload = {"peso_alvo_kg": 500.0}

    response = client.put("/api/metas/3", json=payload, headers=headers_jwt_int)

    assert response.status_code == 400
    res_data = response.get_json()
    assert res_data["erro"] == "Dados inválidos na requisição"


def test_atualizar_meta_nao_encontrada(client, headers_jwt_int):
    """Garante HTTP 404 caso a meta não exista ou não pertença ao usuário."""
    payload = {"peso_alvo_kg": 70.0}

    with patch("services.meta_service.MetaService.atualizar_meta") as mock_service:
        mock_service.return_value = (None, "Meta não encontrada.")

        response = client.put("/api/metas/999", json=payload, headers=headers_jwt_int)

        assert response.status_code == 404
        res_data = response.get_json()
        assert res_data["erro"] == "Meta não encontrada."


# ==============================================================================
# 5. TESTES DE DELETAR META (DELETE /api/metas/<id>)
# ==============================================================================
def test_deletar_meta_sucesso(client, headers_jwt_int):
    """Garante a exclusão bem-sucedida de meta inativa (HTTP 200)."""
    with patch("services.meta_service.MetaService.deletar_meta") as mock_service:
        mock_service.return_value = (True, None)

        response = client.delete("/api/metas/2", headers=headers_jwt_int)

        assert response.status_code == 200
        res_data = response.get_json()
        assert res_data["mensagem"] == "Meta excluída com sucesso!"
        mock_service.assert_called_once_with(meta_id=2, usuario_id=1)


def test_deletar_meta_nao_encontrada_404(client, headers_jwt_int):
    """Garante HTTP 400 caso ocorra erro ao deletar a meta."""
    with patch("services.meta_service.MetaService.deletar_meta") as mock_service:
        mock_service.return_value = (False, "Meta não encontrada.")

        response = client.delete("/api/metas/999", headers=headers_jwt_int)

        assert response.status_code == 400
        res_data = response.get_json()
        assert res_data["erro"] == "Meta não encontrada."


def test_deletar_meta_ativa_regra_negocio_400(client, headers_jwt_int):
    """Garante HTTP 400 caso se tente excluir uma meta que ainda está ativa."""
    with patch("services.meta_service.MetaService.deletar_meta") as mock_service:
        mock_service.return_value = (False, "Não é possível excluir uma meta ativa.")

        response = client.delete("/api/metas/1", headers=headers_jwt_int)

        assert response.status_code == 400
        res_data = response.get_json()
        assert res_data["erro"] == "Não é possível excluir uma meta ativa."


# ==============================================================================
# 6. TESTES DE CANCELAR META (PUT /api/metas/cancelar/<int:meta_id>)
# ==============================================================================
def test_cancelar_meta_sucesso(client, headers_jwt_int):
    """Garante o cancelamento bem-sucedido de uma meta (HTTP 200)."""
    meta_cancelada_mock = {"id": 10, "status": StatusMetaEnum.CANCELADA}

    with patch("services.meta_service.MetaService.cancelar_meta") as mock_service:
        mock_service.return_value = (meta_cancelada_mock, None)

        response = client.put("/api/metas/cancelar/10", headers=headers_jwt_int)

        assert response.status_code == 200
        res_data = response.get_json()
        assert res_data["mensagem"] == "Meta cancelada com sucesso!"
        assert res_data["data"] == meta_cancelada_mock


def test_cancelar_meta_erro_regra_negocio(client, headers_jwt_int):
    """Garante HTTP 400 quando o serviço retorna erro ao cancelar."""
    with patch("services.meta_service.MetaService.cancelar_meta") as mock_service:
        mock_service.return_value = (None, "Meta não encontrada ou já cancelada.")

        response = client.put("/api/metas/cancelar/999", headers=headers_jwt_int)

        assert response.status_code == 400
        res_data = response.get_json()
        assert res_data["erro"] == "Meta não encontrada ou já cancelada."


# ==============================================================================
# 7. TESTES DE LISTAR METAS CONCLUÍDAS (GET /api/metas/concluidas)
# ==============================================================================
def test_listar_metas_concluidas_sucesso(client, headers_jwt_int):
    """Garante a listagem correta das metas concluídas do usuário (HTTP 200)."""
    metas_mock = [
        {"id": 1, "objetivo": Objetivo.MANTER, "status": StatusMetaEnum.CONCLUIDA},
        {"id": 2, "objetivo": Objetivo.GANHAR_MASSA, "status": StatusMetaEnum.CONCLUIDA},
    ]

    with patch("services.meta_service.MetaService.obter_metas_concluidas") as mock_service:
        mock_service.return_value = (metas_mock, None)

        response = client.get("/api/metas/concluidas", headers=headers_jwt_int)

        assert response.status_code == 200
        res_data = response.get_json()
        assert res_data["total"] == 2
        assert res_data["metas"] == metas_mock


def test_listar_metas_concluidas_erro_servico(client, headers_jwt_int):
    """Garante HTTP 400 quando o serviço retorna erro na busca por concluídas."""
    with patch("services.meta_service.MetaService.obter_metas_concluidas") as mock_service:
        mock_service.return_value = (None, "Erro ao buscar metas concluídas.")

        response = client.get("/api/metas/concluidas", headers=headers_jwt_int)

        assert response.status_code == 400
        res_data = response.get_json()
        assert res_data["erro"] == "Erro ao buscar metas concluídas."


# ==============================================================================
# 8. TESTES DE CONCLUIR META (PUT /api/metas/concluir/<int:meta_id>)
# ==============================================================================
def test_concluir_meta_sucesso(client, headers_jwt_int):
    """Garante a conclusão bem-sucedida de uma meta (HTTP 200)."""
    meta_concluida_mock = {"id": 10, "status": StatusMetaEnum.CONCLUIDA}

    with patch("services.meta_service.MetaService.concluir_meta") as mock_service:
        mock_service.return_value = (meta_concluida_mock, None)

        response = client.put("/api/metas/concluir/10", headers=headers_jwt_int)

        assert response.status_code == 200
        res_data = response.get_json()
        assert res_data["mensagem"] == "Meta concluída com sucesso!"
        assert res_data["data"] == meta_concluida_mock


def test_concluir_meta_erro_regra_negocio(client, headers_jwt_int):
    """Garante HTTP 400 quando o serviço retorna erro ao concluir a meta."""
    with patch("services.meta_service.MetaService.concluir_meta") as mock_service:
        mock_service.return_value = (None, "Apenas metas ativas podem ser concluídas.")

        response = client.put("/api/metas/concluir/10", headers=headers_jwt_int)

        assert response.status_code == 400
        res_data = response.get_json()
        assert res_data["erro"] == "Apenas metas ativas podem ser concluídas."