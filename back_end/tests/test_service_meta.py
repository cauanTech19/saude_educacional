import pytest
from unittest.mock import MagicMock, patch
from models import Meta, AvaliacaoFisica, Objetivo, NivelAtividade, StatusMetaEnum
from services.meta_service import MetaService, MULTIPLICADORES_ATIVIDADE


# ==========================================================
# FIXTURES E MOCKS REUTILIZÁVEIS
# ==========================================================

@pytest.fixture
def mock_avaliacao():
    """Mock de uma Avaliação Física com dados válidos."""
    avaliacao = MagicMock(spec=AvaliacaoFisica)
    avaliacao.id = 10
    avaliacao.usuario_id = 1
    avaliacao.tmb = 1800.0
    avaliacao.peso = 80.0
    avaliacao.nivel_atividade_padrao = NivelAtividade.MODERADO
    avaliacao.desativado_em = None
    return avaliacao


@pytest.fixture
def mock_meta():
    """Mock de uma Meta ativa."""
    meta = MagicMock(spec=Meta)
    meta.id = 100
    meta.usuario_id = 1
    meta.avaliacao_origem_id = 10
    meta.objetivo = Objetivo.EMAGRECER
    meta.peso_alvo_kg = 75.0
    meta.calorias_alvo_kcal = 2390.0
    meta.meta_agua_ml = 2800.0
    meta.status = StatusMetaEnum.ATIVA
    meta.concluida_em = None
    meta.to_dict.return_value = {
        "id": 100,
        "usuario_id": 1,
        "objetivo": "EMAGRECER",
        "peso_alvo_kg": 75.0,
        "calorias_alvo_kcal": 2390.0,
        "meta_agua_ml": 2800.0,
        "status": "ATIVA",
    }
    return meta


# ==========================================================
# 1. TESTES DE MÉTODOS AUXILIARES E CÁLCULOS
# ==========================================================
class TestMetaServiceCalculos:
    def test_obter_fator_atividade_enum_valido(self):
        fator = MetaService._obter_fator_atividade(NivelAtividade.INTENSO)
        assert fator == 1.725

    def test_obter_fator_atividade_string_valida(self):
        fator = MetaService._obter_fator_atividade("moderado")
        assert fator == 1.55

    def test_obter_fator_atividade_string_invalida(self):
        fator = MetaService._obter_fator_atividade("INVALIDO")
        assert fator == 1.2  # Valor fallback padrão

    def test_calcular_metricas_meta_emagrecer(self, mock_avaliacao):
        (
            calorias,
            agua,
            proteinas,
            carboidratos,
            gorduras,
        ) = MetaService.calcular_metricas_meta(mock_avaliacao, Objetivo.EMAGRECER)

        assert calorias == 2390.0
        assert agua == 2800.0
        assert proteinas == 160.0
        assert carboidratos == 275.5
        assert gorduras == 72.0

    def test_calcular_metricas_meta_ganhar_massa(self, mock_avaliacao):
        (
            calorias,
            agua,
            proteinas,
            carboidratos,
            gorduras,
        ) = MetaService.calcular_metricas_meta(mock_avaliacao, Objetivo.GANHAR_MASSA)

        assert calorias == 3090.0
        assert agua == 2800.0
        assert proteinas == 160.0
        assert carboidratos == 432.5
        assert gorduras == 80.0

    def test_calcular_metricas_meta_manter(self, mock_avaliacao):
        (
            calorias,
            agua,
            proteinas,
            carboidratos,
            gorduras,
        ) = MetaService.calcular_metricas_meta(mock_avaliacao, Objetivo.MANTER)

        assert calorias == 2790.0
        assert agua == 2800.0
        assert proteinas == 128.0
        assert carboidratos == 389.5
        assert gorduras == 80.0

# ==========================================================
# 2. TESTES: criar_meta
# ==========================================================

class TestCriarMeta:
    @patch("models.db.session")
    def test_criar_meta_sucesso(self, mock_session, mock_avaliacao):
        # Configura o retorno da busca pela avaliação e metas antigas
        mock_session.scalar.return_value = mock_avaliacao
        mock_session.scalars.return_value.all.return_value = []

        dados = {"objetivo": Objetivo.EMAGRECER, "peso_alvo_kg": 75.0}

        res, err = MetaService.criar_meta(usuario_id=1, dados_validados=dados)

        assert err is None
        assert res is not None
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("models.db.session")
    def test_criar_meta_sem_avaliacao_previa(self, mock_session):
        mock_session.scalar.return_value = None  # Nenhuma avaliação encontrada

        dados = {"objetivo": Objetivo.EMAGRECER, "peso_alvo_kg": 75.0}
        res, err = MetaService.criar_meta(usuario_id=1, dados_validados=dados)

        assert res is None
        assert "Você precisa cadastrar ao menos uma avaliação física" in err

    @patch("models.db.session")
    def test_criar_meta_desativa_metas_anteriores(self, mock_session, mock_avaliacao, mock_meta):
        mock_session.scalar.return_value = mock_avaliacao
        mock_session.scalars.return_value.all.return_value = [mock_meta]

        dados = {"objetivo": Objetivo.GANHAR_MASSA, "peso_alvo_kg": 85.0}
        res, err = MetaService.criar_meta(usuario_id=1, dados_validados=dados)

        assert err is None
        # Verifica se a meta antiga foi concluída
        assert mock_meta.status == StatusMetaEnum.CONCLUIDA
        assert mock_meta.concluida_em is not None

    @patch("models.db.session")
    def test_criar_meta_erro_banco(self, mock_session, mock_avaliacao):
        mock_session.scalar.return_value = mock_avaliacao
        mock_session.scalars.return_value.all.return_value = []
        mock_session.commit.side_effect = Exception("Erro de conexão DB")

        dados = {"objetivo": Objetivo.EMAGRECER, "peso_alvo_kg": 75.0}
        res, err = MetaService.criar_meta(usuario_id=1, dados_validados=dados)

        assert res is None
        assert "Erro ao criar meta: Erro de conexão DB" in err
        mock_session.rollback.assert_called_once()


# ==========================================================
# 3. TESTES: obter_meta_ativa & obter_metas_concluidas
# ==========================================================

class TestObterMetas:
    @patch("models.db.session")
    def test_obter_meta_ativa_sucesso(self, mock_session, mock_meta):
        mock_session.scalar.return_value = mock_meta

        res, err = MetaService.obter_meta_ativa(usuario_id=1)

        assert err is None
        assert res["id"] == 100

    @patch("models.db.session")
    def test_obter_meta_ativa_nao_encontrada(self, mock_session):
        mock_session.scalar.return_value = None

        res, err = MetaService.obter_meta_ativa(usuario_id=1)

        assert res is None
        assert err == "Nenhuma meta ativa encontrada."

    @patch("models.db.session")
    def test_obter_metas_concluidas_sucesso(self, mock_session, mock_meta):
        mock_meta.status = StatusMetaEnum.CONCLUIDA
        mock_session.scalars.return_value.all.return_value = [mock_meta]

        res, err = MetaService.obter_metas_concluidas(usuario_id=1)

        assert err is None
        assert len(res) == 1

    @patch("models.db.session")
    def test_obter_metas_concluidas_vazio(self, mock_session):
        mock_session.scalars.return_value.all.return_value = []

        res, err = MetaService.obter_metas_concluidas(usuario_id=1)

        assert res is None
        assert err == "Nenhuma meta concluída foi encontrada."

    @patch("models.db.session")
    def test_obter_metas_concluidas_exception(self, mock_session):
        mock_session.scalars.side_effect = Exception("Falha no DB")

        res, err = MetaService.obter_metas_concluidas(usuario_id=1)

        assert res == []
        assert "Erro ao buscar metas concluídas" in err


# ==========================================================
# 4. TESTES: atualizar_meta
# ==========================================================

class TestAtualizarMeta:
    @patch("models.db.session")
    def test_atualizar_meta_nao_encontrada(self, mock_session):
        mock_session.scalar.return_value = None

        res, err = MetaService.atualizar_meta(meta_id=99, usuario_id=1, dados_validados={})

        assert res is None
        assert err == "Meta não encontrada."

    @patch("models.db.session")
    def test_atualizar_peso_alvo(self, mock_session, mock_meta):
        mock_session.scalar.return_value = mock_meta

        dados = {
            "peso_alvo_kg": 72.0,
            "status": StatusMetaEnum.CONCLUIDA
        }

        res, err = MetaService.atualizar_meta(meta_id=100, usuario_id=1, dados_validados=dados)

        assert err is None
        assert mock_meta.peso_alvo_kg == 72.0
        mock_session.commit.assert_called_once()

    @patch("models.db.session")
    def test_atualizar_objetivo_recalcula_metricas(self, mock_session, mock_meta, mock_avaliacao):
        # 1ª chamada ao scalar traz a meta; 2ª traz a avaliação física
        mock_session.scalar.side_effect = [mock_meta, mock_avaliacao]

        dados = {"objetivo": Objetivo.GANHAR_MASSA}

        res, err = MetaService.atualizar_meta(meta_id=100, usuario_id=1, dados_validados=dados)

        assert err is None
        assert mock_meta.objetivo == Objetivo.GANHAR_MASSA
        assert mock_meta.calorias_alvo_kcal == 3090.0  # Recalculado para superávit
        mock_session.commit.assert_called_once()


# ==========================================================
# 5. TESTES: concluir_meta & cancelar_meta
# ==========================================================

class TestConcluirECancelarMeta:
    @patch("models.db.session")
    def test_concluir_meta_sucesso(self, mock_session, mock_meta):
        mock_session.scalar.return_value = mock_meta

        res, err = MetaService.concluir_meta(meta_id=100, usuario_id=1)

        assert err is None
        assert mock_meta.status == StatusMetaEnum.CONCLUIDA
        mock_session.commit.assert_called_once()

    @patch("models.db.session")
    def test_concluir_meta_status_invalido(self, mock_session, mock_meta):
        mock_meta.status = StatusMetaEnum.CANCELADA
        mock_session.scalar.return_value = mock_meta

        res, err = MetaService.concluir_meta(meta_id=100, usuario_id=1)

        assert res is None
        assert "Apenas metas ativas podem ser concluídas" in err

    @patch("models.db.session")
    def test_cancelar_meta_sucesso(self, mock_session, mock_meta):
        mock_session.scalar.return_value = mock_meta

        res, err = MetaService.cancelar_meta(meta_id=100, usuario_id=1)

        assert err is None
        assert mock_meta.status == StatusMetaEnum.CANCELADA
        mock_session.commit.assert_called_once()


# ==========================================================
# 6. TESTES: deletar_meta
# ==========================================================

class TestDeletarMeta:
    @patch("models.db.session")
    def test_deletar_meta_ativa_proibido(self, mock_session, mock_meta):
        mock_meta.status = StatusMetaEnum.ATIVA
        mock_session.scalar.return_value = mock_meta

        sucesso, err = MetaService.deletar_meta(meta_id=100, usuario_id=1)

        assert sucesso is False
        assert "Não é permitido excluir uma meta ativa" in err

    @patch("models.db.session")
    def test_deletar_meta_inativa_sucesso(self, mock_session, mock_meta):
        mock_meta.status = StatusMetaEnum.CONCLUIDA
        mock_session.scalar.return_value = mock_meta

        sucesso, err = MetaService.deletar_meta(meta_id=100, usuario_id=1)

        assert sucesso is True
        assert err is None
        mock_session.delete.assert_called_once_with(mock_meta)
        mock_session.commit.assert_called_once()