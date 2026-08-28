from datetime import date
import pytest
from unittest.mock import patch
from models import  NivelAtividade, StatusAvaliacaoEnum, Usuario, db
from services.avaliacao_fisica_service import AvaliacaoService


# ==============================================================================
# 1. TESTES UNITÁRIOS (MÉTODOS ESTÁTICOS DE CÁLCULO)
# ==============================================================================

class TestCalculosMetabolicos:
    
    @pytest.mark.parametrize("peso, altura, esperado", [
        (70.0, 1.75, 22.86),   # Peso Normal
        (50.0, 1.70, 17.30),   # Abaixo do Peso
        (90.0, 1.75, 29.39),   # Sobrepeso
        (110.0, 1.75, 35.92),  # Obesidade II
    ])
    def test_calcular_imc_sucesso(self, peso, altura, esperado):
        resultado = AvaliacaoService.calcular_imc(peso, altura)
        assert resultado == esperado

    def test_calcular_imc_altura_invalida_raise_value_error(self):
        with pytest.raises(ValueError, match="Altura deve ser maior que zero."):
            AvaliacaoService.calcular_imc(70.0, 0)

        with pytest.raises(ValueError, match="Altura deve ser maior que zero."):
            AvaliacaoService.calcular_imc(70.0, -1.75)

    @pytest.mark.parametrize("imc, classificacao_esperada", [
        (17.5, 'Abaixo do peso'),
        (18.5, 'Peso normal'),
        (24.9, 'Peso normal'),
        (25.0, 'Sobrepeso'),
        (29.9, 'Sobrepeso'),
        (30.0, 'Obesidade Grau I'),
        (34.9, 'Obesidade Grau I'),
        (35.0, 'Obesidade Grau II'),
        (39.9, 'Obesidade Grau II'),
        (40.0, 'Obesidade Grau III'),
        (45.0, 'Obesidade Grau III'),
    ])
    def test_classificar_imc(self, imc, classificacao_esperada):
        assert AvaliacaoService.classificar_imc(imc) == classificacao_esperada

    @pytest.mark.parametrize("peso, altura_m, idade, sexo, tmb_esperada", [
        # Masculino: (10 * 80) + (6.25 * 180) - (5 * 25) + 5 = 800 + 1125 - 125 + 5 = 1805
        (80.0, 1.80, 25, 'M', 1805.0),
        # Feminino: (10 * 60) + (6.25 * 165) - (5 * 30) - 161 = 600 + 1031.25 - 150 - 161 = 1320.25
        (60.0, 1.65, 30, 'F', 1320.25),
        # Feminino por Extenso
        (60.0, 1.65, 30, 'FEMININO', 1320.25),
    ])
    def test_calcular_tmb(self, peso, altura_m, idade, sexo, tmb_esperada):
        resultado = AvaliacaoService.calcular_tmb(peso, altura_m, idade, sexo)
        assert resultado == tmb_esperada

    def test_calcular_meta_deficit_calorico_padrao(self):
        tmb = 1800.0
        resultado = AvaliacaoService.calcular_meta_deficit_calorico(tmb)

        # TDEE = 1800 * 1.2 = 2160
        # Meta = 2160 - 500 = 1660
        # Deficit = 2160 - 1660 = 500
        assert resultado['tmb'] == 1800.0
        assert resultado['gasto_total_diario'] == 2160.0
        assert resultado['meta_calorias_deficit'] == 1660.0
        assert resultado['deficit_diario'] == 500.0

    def test_calcular_meta_deficit_respeita_piso_seguranca_1200(self):
        tmb = 1000.0  # Gasto baixo
        resultado = AvaliacaoService.calcular_meta_deficit_calorico(
            tmb, fator_atividade=1.2, deficit_desejado=500.0
        )

        # TDEE = 1200
        # TDEE - Deficit = 700 -> Deve bater no piso de 1200.0
        assert resultado['meta_calorias_deficit'] == 1200.0
        assert resultado['deficit_diario'] == 0.0


# ==============================================================================
# 2. TESTES DE INTEGRAÇÃO/PERSISTÊNCIA (SERVICE + BANCO DE DADOS)
# ==============================================================================

@pytest.fixture
def usuario_db(db_session):
    """Fixture que persiste um usuário padrão no banco de dados SQLite de teste."""
    usuario = Usuario(
        nome='Cauan Justino',
        email='cauan@example.com',
        senha_hash='hash123',
        data_nascimento=date(2000, 1, 1),  # 26 anos assumidos
    )
    db_session.add(usuario)
    db_session.commit()
    return usuario


class TestAvaliacaoServiceBD:

    def test_criar_avaliacao_sucesso(self, db_session, usuario_db):
        dados = {
            'peso': 80.0,
            'altura': 1.80,
            'sexo_biologico': 'M',
            'nivel_atividade_padrao': NivelAtividade.SEDENTARIO,
            'cintura': 82.0,
            'quadril': 100.0,
            'braco_relaxado': 35.0,
            'braco_contraido': 38.0,
        }

        avaliacao, erro = AvaliacaoService.criar_avaliacao(usuario_db.id, dados)

        assert erro is None
        assert avaliacao is not None
        assert avaliacao.id is not None
        assert avaliacao.imc == 24.69
        assert avaliacao.tmb > 0
        assert avaliacao.ativo ==  StatusAvaliacaoEnum.ATIVO

    def test_criar_avaliacao_usuario_inexistente(self, db_session):
        dados = {'peso': 70.0, 'altura': 1.70, 'sexo_biologico': 'M'}
        avaliacao, erro = AvaliacaoService.criar_avaliacao(9999, dados)

        assert avaliacao is None
        assert erro == 'Usuário não encontrado.'

    def test_criar_avaliacao_falha_banco_rollback(self, db_session, usuario_db):
        dados = {'peso': 80.0, 'altura': 1.80, 'sexo_biologico': 'M'}

        with patch.object(db_session, 'commit', side_effect=Exception("Erro de conexão DB")):
            avaliacao, erro = AvaliacaoService.criar_avaliacao(usuario_db.id, dados)

            assert avaliacao is None
            assert 'Erro ao salvar avaliação física no banco' in erro

    def test_listar_avaliacoes_usuario(self, db_session, usuario_db):
        # Criar 2 ativas e 1 desativada
        d1 = {"peso": 85.0, "altura": 1.85, "sexo_biologico": 'M', "nivel_atividade_padrao": "leve"}
        d2 = {"peso": 60.0, "altura": 1.65, "sexo_biologico": 'F', "nivel_atividade_padrao": "leve"}
        
        a1, _ = AvaliacaoService.criar_avaliacao(usuario_db.id, d1)
        a2, _ = AvaliacaoService.criar_avaliacao(usuario_db.id, d2)

        # Desativa a primeira
        AvaliacaoService.desativar_avaliacao(a1.id, usuario_db.id)

        # Listar apenas ativas
        ativas = AvaliacaoService.listar_avaliacoes_usuario(usuario_db.id, apenas_ativas=True)
        assert len(ativas) == 1

        # Listar todas
        todas = AvaliacaoService.listar_avaliacoes_usuario(usuario_db.id, apenas_ativas=False)
        assert len(todas) == 2

    def test_atualizar_avaliacao_sucesso_e_recalculo(self, db_session, usuario_db):
        """Garante que a atualização altera os dados e recalcula o IMC corretamente."""
        dados_iniciais = {'peso': 80.0, 'altura': 1.80, 'sexo_biologico': 'M'}
        avaliacao, _ = AvaliacaoService.criar_avaliacao(usuario_db.id, dados_iniciais)
        imc_inicial = avaliacao.imc

        novos_dados = {
            'peso': 90.0,
            'altura': 1.80,
            'cintura': 90.0,
        }

        aval_atualizada, erro = AvaliacaoService.atualizar_avaliacao(
            avaliacao.id, usuario_db.id, novos_dados
        )

        assert erro is None
        assert aval_atualizada.peso == 90.0
        assert aval_atualizada.cintura == 90.0
        assert aval_atualizada.imc > imc_inicial 
        dados = {'peso': 85.0}
        aval, erro = AvaliacaoService.atualizar_avaliacao(999, usuario_db.id, dados)

        assert aval is None
        assert erro == 'Avaliação não encontrada ou desativada.'

    def test_atualizar_avaliacao_erro_campo_extra_proibido(self, db_session, usuario_db):
        """Garante que o Pydantic (extra='forbid') rejeita atualizações com campos desconhecidos."""
        dados_iniciais = {'peso': 80.0, 'altura': 1.80, 'sexo_biologico': 'M'}
        avaliacao, _ = AvaliacaoService.criar_avaliacao(usuario_db.id, dados_iniciais)

        novos_dados = {
            'peso': 90.0,
            'campo_ignorado': 'Ataque Hack' 
        }

        aval_atualizada, erro = AvaliacaoService.atualizar_avaliacao(
            avaliacao.id, usuario_db.id, novos_dados
        )

        assert aval_atualizada is None
        assert erro is not None
        assert "campo_ignorado" in str(erro)

    def test_desativar_e_reativar_avaliacao_soft_delete(self, db_session, usuario_db):
        dados = {"peso": 60.0, "altura": 1.65, "sexo_biologico": 'M', "nivel_atividade_padrao": "leve"}
        aval, _ = AvaliacaoService.criar_avaliacao(usuario_db.id, dados)

        # 1. Desativar
        sucesso, erro = AvaliacaoService.desativar_avaliacao(aval.id, usuario_db.id)
        assert sucesso is True
        assert erro is None
        assert aval.ativo == StatusAvaliacaoEnum.DESATIVADO
        assert aval.desativado_em is not None

        # Tentar desativar novamente (deve falhar)
        sucesso_2, erro_2 = AvaliacaoService.desativar_avaliacao(aval.id, usuario_db.id)
        assert sucesso_2 is False
        assert erro_2 == 'Avaliação não encontrada ou já desativada.'

        # 2. Reativar
        aval_reativada, erro_3 = AvaliacaoService.ativar_avaliacao(aval.id, usuario_db.id)
        assert aval_reativada is not None
        assert erro_3 is None
        assert aval.ativo == StatusAvaliacaoEnum.ATIVO
        assert aval.desativado_em is None