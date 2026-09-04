from models import Usuario, db, TokenBlocklist, select, AceiteTermo
from datetime import timezone, datetime, date
from typing import Optional

class UsuarioService:  
  @staticmethod
  def criar_usuario(dados: dict, ip_cliente: Optional[str] = None) -> tuple[dict | None, str | None]:
      """Regra de negócio para criação de um novo usuário.

      Retorna uma tupla: (usuario_dict, mensagem_de_erro)
      """
      
      email = dados.get('email').lower().strip()

      # 1. Verifica se o e-mail já está cadastrado
      usuario_existente = db.session.scalar(
        db.select(Usuario).where(Usuario.email == email)
      )

      if usuario_existente:
        return None, 'Já existe um usuário cadastrado com este e-mail.'

      try:
        # Converte a string de data caso venha como str do Schema/JSON
        data_nasc = dados['data_nascimento']
        if isinstance(data_nasc, str):
          data_nasc = date.fromisoformat(data_nasc)

        # 2. Cria a instância do Modelo (apenas com a data de nascimento)
        novo_usuario = Usuario(
          nome=dados['nome'],
          email=email,
          data_nascimento=data_nasc,
        )

        # 3. Aplica o Hash da Senha usando o Bcrypt
        novo_usuario.set_senha(dados['senha'])

        registro_aceite = AceiteTermo(
          usuario=novo_usuario, versao_termo='1.0', ip_origem=ip_cliente
        )

        # 4. Persiste no Banco de Dados
        db.session.add(novo_usuario)
        db.session.add(registro_aceite)
        db.session.commit()

        # 5. Monta o dicionário de retorno injetando a idade calculada
        usuario_dict = novo_usuario.to_dict()
        return usuario_dict, None

      except Exception as e:
        db.session.rollback()
        return None, f'Erro ao salvar usuário no banco de dados: {str(e)}'

  @staticmethod
  def limpar_tokens_expirados() -> int:
    """Regra central de expurgo (Art. 15 LGPD): Deleta apenas tokens que já prescreveram."""
    agora = datetime.now(timezone.utc)
    num_deletados = (
      db.session.query(TokenBlocklist)
      .filter(TokenBlocklist.expira_em < agora)
      .delete(synchronize_session=False)
    )

    db.session.commit()
    return num_deletados

  
  @staticmethod
  def autenticar_usuario(email: str, senha: str) -> tuple[Usuario | None, str | None]:
    """Regra de negócio para validação de login."""
    UsuarioService.limpar_tokens_expirados()

    email_limpo = email.lower().strip() if email else ''

    stmt = select(Usuario).where(Usuario.email == email_limpo)
    usuario = db.session.scalar(stmt)

    
    if not usuario or not usuario.checar_senha(senha):
      return None, "E-mail ou senha estão incorretos."

    if not usuario.ativo:
      usuario.ativo = True
      usuario.desativado_em = None
      db.session.commit()

    return usuario, None

  

  @staticmethod
  def atualizar_usuario(usuario_id: int, dados: dict) -> tuple[dict | None, str | None]:
      """Atualiza pontualmente os campos do perfil de forma explícita."""
      usuario = db.session.get(Usuario, usuario_id)    
      if not usuario:
          return None, "Usuário não encontrado."

      try:
          # Atribuições manuais e explícitas
          if "nome" in dados:
            usuario.nome = dados["nome"]

          if "email" in dados:
            usuario.email = dados["email"]

          if "senha" in dados:
            usuario.set_senha(dados["senha"])

          if "data_nascimento" in dados:
            usuario.data_nascimento = dados["data_nascimento"]

          db.session.commit()
          return usuario.to_dict(), None

      except Exception as e:
          db.session.rollback()
          return None, f"Erro ao atualizar perfil: {str(e)}"

  @staticmethod
  def revogar_token(jti: str, expira_em: datetime) -> tuple[bool, str | None]:
    """Adiciona o JTI do token JWT à blocklist para efetuar o logout."""

    UsuarioService.limpar_tokens_expirados()

    try:
        db.session.add(TokenBlocklist(jti=jti, expira_em=expira_em))
        db.session.commit()
        return True, None
    
    except Exception as e:
        db.session.rollback()
        return False, f"Erro ao efetuar logout: {str(e)}"


  @staticmethod
  def desativar_conta(usuario_id: int) -> bool:
    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
      raise ValueError("Usuário não encontrado.")
        
    if not usuario.ativo:
      raise ValueError("Esta conta já está desativada.")

    usuario.ativo = False
    usuario.desativado_em = datetime.now(timezone.utc)
    db.session.commit()
    return True


  @staticmethod
  def deletar_conta_definitivamente(usuario_id: int, senha_confirmacao: str) -> tuple[bool, str | None]:
    """
      Remove o usuário e todos os dados associados em cascata.
      Exige a confirmação da senha atual como trava de segurança.
    """

    usuario = db.session.get(Usuario, usuario_id)

    if not usuario:
      return False, "Usuário não encontrado."

    if not senha_confirmacao:
      raise ValueError("Informe sua senha para confirmar a exclusão.")


    # 1. Trava de segurança: confirmação de senha
    if not usuario.checar_senha(senha_confirmacao):
      return False, "Senha incorreta. Não foi possível excluir a conta."

    db.session.delete(usuario)
    db.session.commit()

    return True, None

  


  @staticmethod
  def obter_por_id(usuario_id: int) -> Usuario:
    usuario = db.session.get(Usuario, usuario_id)
    if not usuario or not usuario.ativo:
      raise ValueError('Usuário não encontrado.')
    return usuario
