from datetime import datetime, date, timezone
from enum import Enum
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy import select

db = SQLAlchemy()
bcrypt = Bcrypt()

# --- ENUMS ---
class SexoBiologico(str, Enum):
    MASCULINO = "M"
    FEMININO = "F"

class NivelAtividade(str, Enum):
    SEDENTARIO = "sedentario"
    LEVE = "leve"
    MODERADO = "moderado"
    INTENSO = "intenso"
    MUITO_INTENSO = "muito_intenso"

class Objetivo(str, Enum):
    EMAGRECER = "emagrecer"
    MANTER = "manter"
    GANHAR_MASSA = "ganhar_massa"

class StatusAvaliacaoEnum(str, Enum):
    ATIVO = 'ATIVO'
    DESATIVADO = 'DESATIVADO'

class StatusMetaEnum(str, Enum):
    ATIVA = "ativa"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"

class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class Usuario(db.Model):
  __tablename__ = 'usuarios'

  id = db.Column(db.Integer, primary_key=True)
  nome = db.Column(db.String(100), nullable=False)
  email = db.Column(db.String(120), unique=True, nullable=False, index=True)
  senha_hash = db.Column(db.String(128), nullable=False)
  data_nascimento = db.Column(db.Date, nullable=False)

  ativo = db.Column(db.Boolean, default=True, nullable=False)
  desativado_em = db.Column(db.DateTime, nullable=True)
  criado_em = db.Column(
    db.DateTime, default=lambda: datetime.now(timezone.utc)
  )

  avaliacoes = db.relationship(
    'AvaliacaoFisica', backref='usuario', cascade='all, delete-orphan'
  )
  metas = db.relationship(
    'Meta', backref='usuario', cascade='all, delete-orphan'
  )
  registros_diarios = db.relationship(
    'RegistroDiario', backref='usuario', cascade='all, delete-orphan'
  )

  def set_senha(self, senha_plana: str):
    self.senha_hash = bcrypt.generate_password_hash(senha_plana).decode('utf-8')

  def checar_senha(self, senha_plana: str) -> bool:
    return bcrypt.check_password_hash(self.senha_hash, senha_plana)

  @property
  def idade_atual(self) -> int:
    hoje = date.today()
    return (
        hoje.year
        - self.data_nascimento.year
        - (
            (hoje.month, hoje.day)
            < (self.data_nascimento.month, self.data_nascimento.day)
        )
    )

  def desativar(self):
    self.ativo = False
    self.desativado_em = datetime.now(timezone.utc)

  def to_dict(self) -> dict:
    return {
        'id': self.id,
        'nome': self.nome,
        'email': self.email,
        'data_nascimento': self.data_nascimento.strftime('%Y-%m-%d'),
        'idade': self.idade_atual,
        'ativo': self.ativo,
        'criado_em': self.criado_em.isoformat() if self.criado_em else None,
    }


class AvaliacaoFisica(db.Model):
  __tablename__ = 'avaliacoes_fisicas'

  id = db.Column(db.Integer, primary_key=True)

  usuario_id = db.Column(
    db.Integer, db.ForeignKey('usuarios.id'), nullable=False
  )

  # Snapshot antropométrico completo no momento da avaliação
  peso = db.Column(db.Float, nullable=False)  # em kg (ex: 75.5)
  altura = db.Column(db.Float, nullable=False)  # em metros (ex: 1.78)
  sexo_biologico = db.Column(db.Enum(SexoBiologico), nullable=False)

  # Métricas Derivadas / Calculadas
  imc = db.Column(db.Float, nullable=False)
  nivel_atividade_padrao = db.Column(
    db.Enum(NivelAtividade), default=NivelAtividade.SEDENTARIO, nullable=False

  )
  tmb = db.Column(db.Float, nullable=True)

  # Circunferências (em cm) - Opcionais
  cintura = db.Column(db.Float, nullable=True)
  quadril = db.Column(db.Float, nullable=True)
  braco_relaxado = db.Column(db.Float, nullable=True)
  braco_contraido = db.Column(db.Float, nullable=True)

  # Status e Controle
  ativo = db.Column(db.Enum(StatusAvaliacaoEnum), default=StatusAvaliacaoEnum.ATIVO, nullable=False)
  desativado_em = db.Column(db.DateTime, nullable=True)
  data_criacao = db.Column(
    db.DateTime, default=lambda: datetime.now(timezone.utc)
  )

  @property
  def idade_na_avaliacao(self) -> int | None:
    """Calcula a idade exata que o usuário tinha no dia em que esta avaliação foi feita."""
    if not self.usuario or not self.usuario.data_nascimento:
      return None

    data_eval = self.data_criacao.date()
    nasc = self.usuario.data_nascimento

    return (
        data_eval.year
        - nasc.year
        - ((data_eval.month, data_eval.day) < (nasc.month, nasc.day))
    )

  def to_dict(self) -> dict:
    return {
        'id': self.id,
        'usuario_id': self.usuario_id,
        'peso': self.peso,
        'altura': self.altura,
        'sexo_biologico': (
            self.sexo_biologico.value
            if isinstance(self.sexo_biologico, Enum)
            else self.sexo_biologico
        ),
        'imc': self.imc,
        'nivel_atividade_padrao': (
            self.nivel_atividade_padrao.value
            if isinstance(self.nivel_atividade_padrao, Enum)
            else self.nivel_atividade_padrao
        ),
        'tmb': self.tmb,
        'cintura': self.cintura,
        'quadril': self.quadril,
        'brazo_relaxado': self.braco_relaxado,
        'brazo_contraido': self.braco_contraido,
        'ativo': self.ativo,
        'desativado_em': (
            self.desativado_em.isoformat() if self.desativado_em else None
        ),
        'data_criacao': (
            self.data_criacao.isoformat() if self.data_criacao else None
        ),
    }


class Meta(db.Model):
    __tablename__ = 'metas'

    id = db.Column(db.Integer, primary_key=True)

    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)

    avaliacao_origem_id = db.Column(db.Integer, db.ForeignKey('avaliacoes_fisicas.id'), nullable=True)

    objetivo = db.Column(db.Enum(Objetivo), nullable=False)
    peso_alvo_kg = db.Column(db.Float, nullable=False)
    calorias_alvo_kcal = db.Column(db.Float, nullable=False)
    meta_agua_ml = db.Column(db.Float, nullable=False)
    status = db.Column(db.Enum(StatusMetaEnum), default=StatusMetaEnum.ATIVA, nullable=False)
    criada_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    concluida_em = db.Column(db.DateTime, nullable=True) 


    def to_dict(self) -> dict:
      return {
        "id": self.id,
        "usuario_id": self.usuario_id,
        "objetivo": self.objetivo.value if isinstance(self.objetivo, Enum) else self.objetivo,
        "peso_alvo_kg": self.peso_alvo_kg,
        "calorias_alvo_kcal": self.calorias_alvo_kcal,
        "meta_agua_ml": self.meta_agua_ml,
        "status": self.status,
        "criada_em": self.criada_em.isoformat() if self.criada_em else None
      }


class RegistroDiario(db.Model):
    __tablename__ = 'registros_diarios'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    data = db.Column(db.Date, default=date.today, nullable=False)
    
    calorias_consumidas_kcal = db.Column(db.Float, default=0.0)
    proteinas_g = db.Column(db.Float, default=0.0)
    carboidratos_g = db.Column(db.Float, default=0.0)
    gorduras_g = db.Column(db.Float, default=0.0)
    agua_consumida_ml = db.Column(db.Float, default=0.0)
    exercicio_realizado = db.Column(db.Boolean, default=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "data": self.data.strftime('%Y-%m-%d'),
            "calorias_consumidas_kcal": self.calorias_consumidas_kcal,
            "proteinas_g": self.proteinas_g,
            "carboidratos_g": self.carboidratos_g,
            "gorduras_g": self.gorduras_g,
            "agua_consumida_ml": self.agua_consumida_ml,
            "exercicio_realizado": self.exercicio_realizado
        }