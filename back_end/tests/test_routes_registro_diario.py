import pytest
from datetime import date
from schemas.registro_diario import RegistroDiarioCreateSchema
from services.registro_diario_service import RegistroDiarioService
from models import Meta, Objetivo

class TestRegistroDiarioRoutes:

    def test_criar_registro_sucesso(self, client, db_session, meta_db_ativa, auth_headers):
        payload = {
            "meta_id": meta_db_ativa.id,
            "calorias_consumidas_kcal": 2000.0,
            "proteinas_g": 150.0,
            "carboidratos_g": 200.0,
            "gorduras_g": 60.0,
            "agua_consumida_ml": 2500.0,
            "exercicio_realizado": True,
            "peso_registro_kg": 75.5,
            "observacoes": "Treino intenso"
        }

        response = client.post("/registros/diarios/", json=payload, headers=auth_headers)
        if response.status_code != 201:
            print("\n[RESPOSTA DA ROTA]:", response.get_json()) 

        assert response.status_code == 201
        data = response.get_json()
        assert "registro" in data
        assert "feedback" in data
        assert data["registro"]["usuario_id"] == 1
        assert data["registro"]["calorias_consumidas_kcal"] == 2000.0

    def test_criar_registro_meta_invalida(self, client, auth_headers):
        payload = {
            "meta_id": 99999,  # Meta inexistente
            "calorias_consumidas_kcal": 2000.0,
            "proteinas_g": 150.0,
            "carboidratos_g": 200.0,
            "gorduras_g": 60.0,
            "agua_consumida_ml": 2500.0
        }

        response = client.post("/registros/diarios/", json=payload, headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert "erro" in data

    def test_buscar_registro_por_id_sucesso(self, client, db_session, meta_db_ativa, auth_headers):
        dados_criacao = RegistroDiarioCreateSchema(
            meta_id=meta_db_ativa.id,
            calorias_consumidas_kcal=2200.0,
            proteinas_g=140.0,
            carboidratos_g=210.0,
            gorduras_g=55.0,
            agua_consumida_ml=3000.0
        )
        res = RegistroDiarioService.criar_registro(usuario_id=1, dados=dados_criacao)
        registro_id = res["registro"].id

        response = client.get(f"/registros/diarios/{registro_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == registro_id
        assert data["calorias_consumidas_kcal"] == 2200.0

    def test_buscar_registro_por_id_nao_encontrado(self, client, auth_headers):
        response = client.get("/registros/diarios/99999", headers=auth_headers)

        assert response.status_code == 404
        assert response.get_json()["erro"] == "Registro diário não encontrado."


    def test_atualizar_registro_sucesso(self, client, db_session, meta_db_ativa, auth_headers):
        dados_iniciais = RegistroDiarioCreateSchema(
            meta_id=meta_db_ativa.id,
            calorias_consumidas_kcal=1500.0,
            proteinas_g=100.0,
            carboidratos_g=200.0,
            gorduras_g=50.0,
            agua_consumida_ml=1500.0
        )
        res_criacao = RegistroDiarioService.criar_registro(usuario_id=1, dados=dados_iniciais)
        registro_id = res_criacao["registro"].id

        payload_update = {
            "calorias_consumidas_kcal": 2600.0,
            "proteinas_g": 165.0,
            "agua_consumida_ml": 3000.0
        }

        response = client.put(f"/registros/diarios/{registro_id}", json=payload_update, headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["registro"]["calorias_consumidas_kcal"] == 2600.0
        assert data["registro"]["proteinas_g"] == 165.0
        assert data["registro"]["agua_consumida_ml"] == 3000.0
        assert "feedback" in data

    def test_atualizar_registro_nao_encontrado(self, client, auth_headers):
        payload_update = {"calorias_consumidas_kcal": 2000.0}

        response = client.put("/registros/diarios/99999", json=payload_update, headers=auth_headers)

        assert response.status_code == 404
        assert response.get_json()["erro"] == "Registro diário não encontrado."

    def test_deletar_registro_sucesso(self, client, db_session, meta_db_ativa, auth_headers):
        dados_criacao = RegistroDiarioCreateSchema(
            meta_id=meta_db_ativa.id,
            calorias_consumidas_kcal=1900.0,
            proteinas_g=110.0,
            carboidratos_g=190.0,
            gorduras_g=45.0,
            agua_consumida_ml=2200.0
        )
        res = RegistroDiarioService.criar_registro(usuario_id=1, dados=dados_criacao)
        registro_id = res["registro"].id

        response = client.delete(f"/registros/diarios/{registro_id}", headers=auth_headers)

        assert response.status_code == 200
        assert response.get_json()["mensagem"] == "Registro diário foi removido com sucesso."

        # Garante que não é mais encontrado no banco após deleção
        registro_db = RegistroDiarioService.buscar_por_id(usuario_id=1, registro_id=registro_id)
        assert registro_db is None

    def test_deletar_registro_nao_encontrado(self, client, auth_headers):
        response = client.delete("/registros/diarios/99999", headers=auth_headers)

        assert response.status_code == 404
        assert response.get_json()["erro"] == "Registro diário não encontrado."