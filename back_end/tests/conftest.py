import sys
from pathlib import Path
from datetime import date
import pytest

# Adiciona o diretório 'back_end' ao caminho de busca do Python
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app import create_app
from models import db, Usuario, Meta, Objetivo
from flask_jwt_extended import create_access_token
from services.user_service import UsuarioService

@pytest.fixture
def app():
    app = create_app(test_config=True)
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "chave_super_secreta_para_testes_de_32_bytes_minimo",
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def auth_headers(usuario_db):
    """Gera token válido para o usuário criado no banco."""
    token = create_access_token(identity=str(usuario_db.id))
        
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"

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



@pytest.fixture
def db_session(app):
    """Fixture que fornece a sessão do banco dentro do contexto da aplicação."""
    with app.app_context():
        yield db.session


@pytest.fixture
def client(app):
    """Cliente HTTP para simular requisições nas rotas."""
    return app.test_client()


@pytest.fixture
def dados_usuario_validos():
    """Massa de dados padrão para testes."""
    return {
        "nome": "Carlos Eduardo",
        "email": "carlos@exemplo.com",
        "senha": "senhaSegura123!@",
        "data_nascimento": "1995-08-15",
        "aceitou_termos": True,
    }


@pytest.fixture
def usuario_para_deletar(db_session):
    """Fixture que cria um usuário cadastrado e gera o token de acesso JWT."""
    payload = {
        "nome": "Cauan Justino",
        "email": "cauan_delete@teste.com",
        "senha": "senha_segura123",
        "data_nascimento": "2006-04-17",
    }
    usuario_dict, _ = UsuarioService.criar_usuario(payload)

    # Gera token autenticado
    access_token = create_access_token(identity=str(usuario_dict["id"]))

    return {
        "id": usuario_dict["id"],
        "email": payload["email"],
        "senha": payload["senha"],
        "token": access_token,
    }



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




@pytest.fixture
def usuario_db(db_session, dados_usuario_validos):
    """Cria e persiste um usuário no banco mantendo o objeto vinculado à sessão."""
    user = Usuario(
        nome=dados_usuario_validos["nome"],
        email=dados_usuario_validos["email"],
        data_nascimento=date.fromisoformat(dados_usuario_validos["data_nascimento"]),
    )
    user.set_senha(dados_usuario_validos["senha"])
    
    db_session.add(user)
    db_session.commit()
    return user