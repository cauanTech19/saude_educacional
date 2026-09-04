from datetime import datetime, timedelta, timezone
import pytest
from models import AceiteTermo, TokenBlocklist, Usuario, db
from services.user_service import UsuarioService


# ==============================================================================
# TESTES DE CRIAÇÃO DE USUÁRIO
# ==============================================================================
def test_criar_usuario_sucesso(db_session, dados_usuario_validos):
    """Testa a criação de usuário com registro de auditoria do aceite de termos."""
    ip_cliente = "192.168.1.1"
    usuario_dict, erro = UsuarioService.criar_usuario(
        dados_usuario_validos, ip_cliente=ip_cliente
    )

    assert erro is None
    assert usuario_dict is not None
    assert usuario_dict["email"] == dados_usuario_validos["email"].lower()

    # Valida se persistiu no banco
    usuario_db = db.session.scalar(
        db.select(Usuario).where(
            Usuario.email == dados_usuario_validos["email"].lower()
        )
    )
    assert usuario_db is not None
    assert usuario_db.checar_senha(dados_usuario_validos["senha"])

    # Valida auditoria LGPD (AceiteTermo)
    aceite_db = db.session.scalar(
        db.select(AceiteTermo).where(AceiteTermo.usuario_id == usuario_db.id)
    )
    assert aceite_db is not None
    assert aceite_db.versao_termo == "1.0"
    assert aceite_db.ip_origem == ip_cliente


def test_criar_usuario_email_duplicado(db_session, dados_usuario_validos):
    """Garante que não seja permitido cadastrar e-mails duplicados."""
    UsuarioService.criar_usuario(dados_usuario_validos)

    # Tenta cadastrar novamente com variação de maiúsculas/espaços
    dados_duplicados = dados_usuario_validos.copy()
    dados_duplicados["email"] = " carlos@exemplo.com "

    usuario_dict, erro = UsuarioService.criar_usuario(dados_duplicados)

    assert usuario_dict is None
    assert erro == "Já existe um usuário cadastrado com este e-mail."


# ==============================================================================
# TESTES DE AUTENTICAÇÃO
# ==============================================================================
def test_autenticar_usuario_sucesso(db_session, dados_usuario_validos):
    """Valida o login correto com normalização de e-mail."""
    UsuarioService.criar_usuario(dados_usuario_validos)

    usuario, erro = UsuarioService.autenticar_usuario(
        "carlos@exemplo.com", "senhaSegura123!@"
    )

    assert erro is None
    assert usuario is not None
    assert usuario.email == dados_usuario_validos["email"].lower()


def test_autenticar_usuario_senha_incorreta(db_session, dados_usuario_validos):
    """Verifica se bloqueia login quando a senha estiver errada."""
    UsuarioService.criar_usuario(dados_usuario_validos)

    usuario, erro = UsuarioService.autenticar_usuario(
        dados_usuario_validos["email"], "senha_errada"
    )

    assert usuario is None
    assert erro == "E-mail ou senha estão incorretos."


def test_autenticar_usuario_reativacao_automatica(db_session, dados_usuario_validos):
    """Garante que logar em uma conta desativada a reative automaticamente."""
    usuario_dict, _ = UsuarioService.criar_usuario(dados_usuario_validos)
    UsuarioService.desativar_conta(usuario_dict["id"])

    # Tenta autenticar na conta desativada
    usuario, erro = UsuarioService.autenticar_usuario(
        dados_usuario_validos["email"], dados_usuario_validos["senha"]
    )

    assert erro is None
    assert usuario.ativo is True
    assert usuario.desativado_em is None


# ==============================================================================
# TESTES DE BLOCKLIST DE TOKENS
# ==============================================================================
def test_limpar_tokens_expirados(db_session):
    """Testa o expurgo de tokens vencidos respeitando a retention da LGPD."""
    agora = datetime.now(timezone.utc)

    # Token 1: Expirou há 10 minutos (Deve ser deletado)
    token_expirado = TokenBlocklist(
        jti="token-expirado-123", expira_em=agora - timedelta(minutes=10)
    )

    # Token 2: Expira em 10 minutos no futuro (Deve ser mantido)
    token_valido = TokenBlocklist(
        jti="token-valido-456", expira_em=agora + timedelta(minutes=10)
    )

    db.session.add_all([token_expirado, token_valido])
    db.session.commit()

    # Executa o expurgo
    num_deletados = UsuarioService.limpar_tokens_expirados()

    assert num_deletados == 1

    # Verifica o estado no banco
    tokens_restantes = db.session.scalars(db.select(TokenBlocklist)).all()
    assert len(tokens_restantes) == 1
    assert tokens_restantes[0].jti == "token-valido-456"


def test_revogar_token(db_session):
    """Valida a inclusão do JTI na blocklist e acionamento automático da limpeza."""
    expira_em = datetime.now(timezone.utc) + timedelta(hours=1)
    sucesso, erro = UsuarioService.revogar_token("jti-teste-789", expira_em)

    assert sucesso is True
    assert erro is None

    token_db = db.session.scalar(
        db.select(TokenBlocklist).where(TokenBlocklist.jti == "jti-teste-789")
    )
    assert token_db is not None


# ==============================================================================
# TESTES DE ATUALIZAÇÃO E CONSULTA DE PERFIL
# ==============================================================================
def test_atualizar_usuario_sucesso(db_session, dados_usuario_validos):
    """Testa a atualização pontual de campos do perfil."""
    usuario_dict, _ = UsuarioService.criar_usuario(dados_usuario_validos)

    novos_dados = {
        "nome": "Cauan Justino Refatorado",
        "email": "cauan_novo@teste.com",
    }
    usuario_atualizado, erro = UsuarioService.atualizar_usuario(
        usuario_dict["id"], novos_dados
    )

    assert erro is None
    assert usuario_atualizado["nome"] == "Cauan Justino Refatorado"
    assert usuario_atualizado["email"] == "cauan_novo@teste.com"


def test_obter_por_id_sucesso_e_erro(db_session, dados_usuario_validos):
    """Valida a busca por ID e a rejeição para contas inexistentes ou inativas."""
    usuario_dict, _ = UsuarioService.criar_usuario(dados_usuario_validos)

    # Sucesso
    usuario = UsuarioService.obter_por_id(usuario_dict["id"])
    assert usuario.id == usuario_dict["id"]

    # Desativa a conta
    UsuarioService.desativar_conta(usuario_dict["id"])

    # Deve lançar ValueError para usuário inativo
    with pytest.raises(ValueError, match="Usuário não encontrado."):
        UsuarioService.obter_por_id(usuario_dict["id"])


# ==============================================================================
# TESTES DE DESATIVAÇÃO E DELEÇÃO (DIREITO AO ESQUECIMENTO / LGPD)
# ==============================================================================
def test_desativar_conta_sucesso(db_session, dados_usuario_validos):
    """Testa o Soft Delete (desativação temporária)."""
    usuario_dict, _ = UsuarioService.criar_usuario(dados_usuario_validos)

    resultado = UsuarioService.desativar_conta(usuario_dict["id"])
    assert resultado is True

    usuario_db = db.session.get(Usuario, usuario_dict["id"])
    assert usuario_db.ativo is False
    assert usuario_db.desativado_em is not None


def test_deletar_conta_definitivamente_sucesso(db_session, dados_usuario_validos):
    """Testa o Hard Delete confirmando a trava de segurança por senha."""
    usuario_dict, _ = UsuarioService.criar_usuario(dados_usuario_validos)

    # Tenta apagar com senha errada
    sucesso, erro = UsuarioService.deletar_conta_definitivamente(
        usuario_dict["id"], "senha_errada"
    )
    assert sucesso is False
    assert (
        erro == "Senha incorreta. Não foi possível excluir a conta."
    )

    # Apaga com a senha correta
    sucesso, erro = UsuarioService.deletar_conta_definitivamente(
        usuario_dict["id"], dados_usuario_validos["senha"]
    )
    assert sucesso is True
    assert erro is None

    # Garante a exclusão física do banco
    usuario_db = db.session.get(Usuario, usuario_dict["id"])
    assert usuario_db is None