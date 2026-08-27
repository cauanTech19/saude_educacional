from datetime import date
from unittest.mock import MagicMock
import pytest
from models import Meta, Objetivo
from schemas.registro_diario import RegistroDiarioCreateSchema, RegistroDiarioUpdateSchema
from services.registro_diario_service import RegistroDiarioService


# ==========================================================
# FIXTURES
# ==========================================================
@pytest.fixture
def mock_meta_base():
    """Mock básico de meta para testes unitários isolados."""
    meta = MagicMock()
    meta.calorias_alvo_kcal = 2000.0
    meta.proteinas_alvo_g = 150.0
    meta.carboidratos_alvo_g = 200.0
    meta.gorduras_alvo_g = 60.0
    meta.meta_agua_ml = 3000.0
    return meta


@pytest.fixture
def mock_registro_base():
    """Mock básico de registro para testes unitários isolados."""
    registro = MagicMock()
    registro.calorias_consumidas_kcal = 2000.0
    registro.proteinas_g = 150.0
    registro.carboidratos_g = 200.0
    registro.gorduras_g = 60.0
    registro.agua_consumida_ml = 3000.0
    return registro



@pytest.fixture
def meta_db_ativa(db_session):
    """Insere uma meta real no banco em memória para testar o CRUD."""
    meta = Meta(
        id=1,
        usuario_id=1,
        objetivo=Objetivo.GANHAR_MASSA,
        calorias_alvo_kcal=2500.0,
        peso_alvo_kg=75.0,
        proteinas_alvo_g=160.0,
        carboidratos_alvo_g=300.0,
        gorduras_alvo_g=70.0,
        meta_agua_ml=3000.0,
    )
    db_session.add(meta)
    db_session.commit()
    db_session.refresh(meta)
    return meta


# ==========================================================
# TESTES UNITÁRIOS: REGRAS DE NEGÓCIO E FEEDBACK
# ==========================================================
class TestGanhoMassa:

    def test_ganho_massa_sucesso(self, mock_registro_base, mock_meta_base):
        resultado = RegistroDiarioService.avaliar_ganho_massa(
            mock_registro_base, mock_meta_base
        )

        assert resultado["sucesso"] is True
        assert resultado["objetivo"] == Objetivo.GANHAR_MASSA
        assert "Excelente dia" in resultado["mensagem"]
        assert resultado["detalhes"]["proteina_ok"] is True
        assert resultado["detalhes"]["calorias_ok"] is True

    def test_ganho_massa_falha_calorias_e_agua(
        self, mock_registro_base, mock_meta_base
    ):
        mock_registro_base.calorias_consumidas_kcal = 1500.0
        mock_registro_base.agua_consumida_ml = 2000.0

        resultado = RegistroDiarioService.avaliar_ganho_massa(
            mock_registro_base, mock_meta_base
        )

        assert resultado["sucesso"] is False
        assert "calorias abaixo do necessário" in resultado["mensagem"]
        assert "meta de água não atingida" in resultado["mensagem"]
        assert resultado["detalhes"]["calorias_ok"] is False
        assert resultado["detalhes"]["agua_ok"] is False


class TestEmagrecimento:
    def test_emagrecimento_sucesso(self, mock_registro_base, mock_meta_base):
        resultado = RegistroDiarioService.avaliar_emagrecimento(
            mock_registro_base, mock_meta_base
        )

        assert resultado["sucesso"] is True
        assert resultado["objetivo"] == Objetivo.EMAGRECER
        assert "Déficit calórico mantido" in resultado["mensagem"]

    def test_emagrecimento_falha_excesso_calorias_e_gordura(
        self, mock_registro_base, mock_meta_base
    ):
        mock_registro_base.calorias_consumidas_kcal = 2500.0
        mock_registro_base.gorduras_g = 80.0

        resultado = RegistroDiarioService.avaliar_emagrecimento(
            mock_registro_base, mock_meta_base
        )

        assert resultado["sucesso"] is False
        assert "ultrapassou o teto calórico" in resultado["mensagem"]
        assert "gorduras acima do teto planejado" in resultado["mensagem"]


class TestManutencao:

    def test_manutencao_sucesso_dentro_da_margem_5_percento(
        self, mock_registro_base, mock_meta_base
    ):
        mock_registro_base.calorias_consumidas_kcal = 2080.0

        resultado = RegistroDiarioService.avaliar_manutencao(
            mock_registro_base, mock_meta_base
        )

        assert resultado["sucesso"] is True
        assert resultado["detalhes"]["calorias_ok"] is True
        assert "Balanço mantido" in resultado["mensagem"]

    def test_manutencao_falha_calorias_muito_acima(
        self, mock_registro_base, mock_meta_base
    ):
        mock_registro_base.calorias_consumidas_kcal = 2200.0

        resultado = RegistroDiarioService.avaliar_manutencao(
            mock_registro_base, mock_meta_base
        )

        assert resultado["sucesso"] is False
        assert "calorias muito acima da manutenção" in resultado["mensagem"]

    def test_manutencao_falha_calorias_muito_abaixo(
        self, mock_registro_base, mock_meta_base
    ):
        mock_registro_base.calorias_consumidas_kcal = 1700.0

        resultado = RegistroDiarioService.avaliar_manutencao(
            mock_registro_base, mock_meta_base
        )

        assert resultado["sucesso"] is False
        assert "calorias muito abaixo da manutenção" in resultado["mensagem"]


class TestGerarFeedbackDiarioRouter:

    @pytest.mark.parametrize(
        "objetivo_enum",
        [
            Objetivo.GANHAR_MASSA,
            Objetivo.EMAGRECER,
            Objetivo.MANTER,
        ],
    )
    def test_roteamento_correto_por_objetivo(
        self,
        mock_registro_base,
        mock_meta_base,
        objetivo_enum,
    ):
        mock_meta_base.objetivo = objetivo_enum

        res = RegistroDiarioService.gerar_feedback_diario(
            mock_registro_base, mock_meta_base
        )

        assert res["objetivo"] == objetivo_enum

    def test_roteamento_objetivo_desconhecido(
        self, mock_registro_base, mock_meta_base
    ):
        mock_meta_base.objetivo = "DESCONHECIDO"

        res = RegistroDiarioService.gerar_feedback_diario(
            mock_registro_base, mock_meta_base
        )

        assert res["objetivo"] == "GERAL"
        assert res["mensagem"] == "Registro salvo com sucesso!"


# ==========================================================
# TESTES DE INTEGRAÇÃO: OPERAÇÕES CRUD (SQLAlchemy + SQLite)
# ==========================================================
class TestCriarRegistroCRUD:

    def test_criar_registro_sucesso(self, db_session, meta_db_ativa):
        dados = RegistroDiarioCreateSchema(
            meta_id=meta_db_ativa.id,
            calorias_consumidas_kcal=2600.0,
            proteinas_g=170.0,
            carboidratos_g=310.0,
            gorduras_g=70.0,
            agua_consumida_ml=3000.0,
            exercicio_realizado=True,
            peso_registro_kg=75.5,
            observacoes="Treino intenso",
        )

        resultado = RegistroDiarioService.criar_registro(
          usuario_id=1, dados=dados
        )

        registro = resultado["registro"]
        feedback = resultado["feedback"]

        assert registro.id is not None
        assert registro.usuario_id == 1
        assert registro.meta_id == meta_db_ativa.id
        assert registro.data == date.today()
        assert feedback["sucesso"] is True
        assert feedback["objetivo"] == Objetivo.GANHAR_MASSA

    def test_criar_registro_meta_inexistente_erro(self, db_session):
        dados = RegistroDiarioCreateSchema(
            meta_id=999,
            calorias_consumidas_kcal=2000.0,
            proteinas_g=100.0,
            carboidratos_g=150.0,
            gorduras_g=50.0,
            agua_consumida_ml=2000.0,
        )

        with pytest.raises(ValueError) as exc_info:
            RegistroDiarioService.criar_registro(
                usuario_id=1, dados=dados
            )

        assert "Meta não encontrada ou não pertence ao usuário" in str(
            exc_info.value
        )


class TestBuscarRegistroCRUD:
    def test_buscar_por_id_sucesso(self, db_session, meta_db_ativa):
        dados = RegistroDiarioCreateSchema(
            meta_id=meta_db_ativa.id,
            calorias_consumidas_kcal=2000.0,
            proteinas_g=150.0,
            carboidratos_g=200.0,
            gorduras_g=60.0,
            agua_consumida_ml=2500.0,
        )
        res_criacao = RegistroDiarioService.criar_registro(
           usuario_id=1, dados=dados
        )
        registro_id = res_criacao["registro"].id

        registro_encontrado = RegistroDiarioService.buscar_por_id(
           usuario_id=1, registro_id=registro_id
        )

        assert registro_encontrado is not None
        assert registro_encontrado.id == registro_id



class TestAtualizarERemoverRegistroCRUD:

    def test_atualizar_registro_sucesso(self, db_session, meta_db_ativa):
        # 1. Cria o registro inicial
        dados_iniciais = RegistroDiarioCreateSchema(
            meta_id=meta_db_ativa.id,
            calorias_consumidas_kcal=1500.0,
            proteinas_g=100.0,
            carboidratos_g=200.0,
            gorduras_g=50.0,
            agua_consumida_ml=1500.0,
        )
        res_criacao = RegistroDiarioService.criar_registro(
            usuario_id=1, dados=dados_iniciais
        )
        registro_id = res_criacao["registro"].id

        # 2. Instancia o schema de atualização com os campos parciais
        dados_atualizacao = RegistroDiarioUpdateSchema(
            calorias_consumidas_kcal=2600.0,
            proteinas_g=165.0,
            agua_consumida_ml=3000.0,
        )

        # 3. Executa a atualização via serviço
        res_update = RegistroDiarioService.atualizar_registro(
            usuario_id=1,
            registro_id=registro_id,
            dados=dados_atualizacao,
        )

        registro_atualizado = res_update["registro"]
        feedback = res_update["feedback"]

        # 4. Assertivas dos dados atualizados
        assert registro_atualizado.calorias_consumidas_kcal == 2600.0
        assert registro_atualizado.proteinas_g == 165.0
        assert registro_atualizado.agua_consumida_ml == 3000.0
        
        # Valida que os campos não enviados na atualização mantiveram seus valores originais
        assert registro_atualizado.carboidratos_g == 200.0
        assert registro_atualizado.gorduras_g == 50.0
        
        # Valida a reavaliação do feedback nutricional
        assert feedback["sucesso"] is True
        
    def test_deletar_registro_sucesso(self, db_session, meta_db_ativa):
        dados = RegistroDiarioCreateSchema(
            meta_id=meta_db_ativa.id,
            calorias_consumidas_kcal=2000.0,
            proteinas_g=150.0,
            carboidratos_g=200.0,
            gorduras_g=60.0,
            agua_consumida_ml=2500.0,
        )
        res_criacao = RegistroDiarioService.criar_registro(
            usuario_id=1, dados=dados
        )
        registro_id = res_criacao["registro"].id

        sucesso = RegistroDiarioService.deletar_registro(
            usuario_id=1, registro_id=registro_id
        )

        registro_consultado = RegistroDiarioService.buscar_por_id(
            usuario_id=1, registro_id=registro_id
        )

        assert sucesso is True
        assert registro_consultado is None