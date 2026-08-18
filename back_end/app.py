import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from models import TokenBlocklist
from rotas.rota_user import auth_bp
from rotas.rota_avaliacao_fisica import avaliacao_bp
from models import bcrypt, db
from rotas.rota_meta import meta_bp


load_dotenv()

def create_app(test_config=False):
  app = Flask(__name__)
  CORS(app)

  if test_config:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
  else:
    database_url = os.getenv(
      'DATABASE_URL', 'sqlite:///saude_educacional.db'
    )
    if database_url and database_url.startswith('mysql://'):
      database_url = database_url.replace('mysql://', 'mysql+pymysql://')

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url

  app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
  app.config['JWT_SECRET_KEY'] = os.getenv(
    'JWT_SECRET_KEY', 'chave-secreta-padrao-dev'
  )

  # Inicializa as extensões
  db.init_app(app)
  bcrypt.init_app(app)
  jwt = JWTManager(app)

  @jwt.token_in_blocklist_loader
  def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    jti = jwt_payload["jti"]
    token = db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar()
    return token is not None

  app.register_blueprint(auth_bp, url_prefix='/api/auth')
  app.register_blueprint(avaliacao_bp, url_prefix='/api/avaliacoes')
  app.register_blueprint(meta_bp, url_prefix='/api/metas')


  return app

app = create_app()

if __name__ == '__main__':
  with app.app_context():
    db.create_all()  # Cria as tabelas se não existirem
  app.run(host='0.0.0.0', debug=True, port=5000)