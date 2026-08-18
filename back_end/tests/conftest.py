import sys
from pathlib import Path
from datetime import date
import pytest

# Adiciona o diretório 'back_end' ao caminho de busca do Python
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app import create_app
from models import db, Usuario


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
    }


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