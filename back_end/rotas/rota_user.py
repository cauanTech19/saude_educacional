from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
from schemas.user import UsuarioLoginSchema, UsuarioUpdateSchema, UsuarioSchema
from services.user_service import UsuarioService
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime, timezone

auth_bp = Blueprint('auth', __name__)

@auth_bp.post('/register')
def register():
  dados_brutos = request.get_json() or {}
  schema = UsuarioSchema(**dados_brutos)
  dados_validados = schema.model_dump(exclude_unset=True)


  # 1. Extração segura do IP real do cliente (compatível com Docker e Nginx)
  ip_cliente = request.headers.get(
    'X-Forwarded-For', request.remote_addr
  )

  if ip_cliente and ',' in ip_cliente:
    # Se houver múltiplos proxies encadeados, pega o primeiro IP da lista (o do cliente)
    ip_cliente = ip_cliente.split(',')[0].strip()

    # 2. Envia o payload bruto e o IP para o Service validar no Pydantic e registrar o aceite
  usuario_criado, erro = UsuarioService.criar_usuario(
    dados=dados_validados, ip_cliente=ip_cliente
  )

  if erro:
    return jsonify({'erros': erro}), 400

  return (
    jsonify(
      {
        'mensagem': 'Usuário cadastrado com sucesso!',
        'usuario': usuario_criado,
      }
        ), 201,

    )

@auth_bp.post('/login')
def login():
  dados_requisicao = request.get_json() or {}
  dados_validados = UsuarioLoginSchema(**dados_requisicao).model_dump()

  # 2. Autenticação no Service
  usuario, erro = UsuarioService.autenticar_usuario(
    dados_validados['email'], dados_validados['senha']
  )

  if erro:
    return jsonify({'mensagem': erro}), 401

  # 3. Geração do Token JWT
  access_token = create_access_token(identity=str(usuario.id))

  return (
      jsonify({
      'access_token': access_token,
      'token_type': 'Bearer',
      'usuario': usuario.to_dict(),
    }), 200,
  )

@auth_bp.put('/atualizar')
@jwt_required()
def atualizar_perfil():
  usuario_id = int(get_jwt_identity())
  dados = request.get_json() or {}
  dados_validados = UsuarioUpdateSchema(**dados).model_dump(exclude_unset=True)

  usuario_atualizado, erro = UsuarioService.atualizar_usuario(usuario_id, dados_validados)

  if erro:
    return jsonify({'mensagem': erro}), 400

  return jsonify({
    'mensagem': 'Perfil atualizado com sucesso!',
    'usuario': usuario_atualizado
  }), 200


@auth_bp.post('/logout')
@jwt_required()
def logout():
  jwt_data = get_jwt()
  jti = jwt_data['jti']

  # 1. Extrai o timestamp de expiração do JWT e converte para datetime (UTC)
  exp_timestamp = jwt_data['exp']
  expira_em = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

  # 2. Passa o jti e o expira_em para o Service
  sucesso, erro = UsuarioService.revogar_token(
    jti=jti, expira_em=expira_em
  )

  if erro:
    return jsonify({'mensagem': erro}), 500

  return (
    jsonify(
        {'mensagem': 'Logout realizado com sucesso! Token revogado.'}
    ), 200,
  )

@auth_bp.delete('/desativar')
@jwt_required()
def desativar_conta():
  try:
    usuario_id = int(get_jwt_identity())
    UsuarioService.desativar_conta(usuario_id)
    return jsonify({'mensagem': 'Conta desativada com sucesso.'}), 200

  except ValueError as e:
    return jsonify({'erro': str(e)}), 400
  
  except Exception as e:
    return jsonify({'erro': 'Erro interno ao desativar conta.'}), 500



@auth_bp.delete('/deletar')
@jwt_required()
def deletar_minha_conta():
    try:
        usuario_id = int(get_jwt_identity())
        dados = request.get_json() or {}
        senha = dados.get('senha')

        sucesso, erro = UsuarioService.deletar_conta_definitivamente(
            usuario_id, senha
        )

        if not sucesso:
            return jsonify({'erro': erro}), 400

        return (
            jsonify({
                'mensagem': (
                    'Conta e todos os dados pessoais associados foram excluídos'
                    ' com sucesso.'
                )
            }),
            200,
        )
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    except Exception:
        return jsonify({'erro': 'Erro ao deletar o perfil.'}), 500


    
@auth_bp.get('/info')
@jwt_required()
def obter_perfil():
  try:
    usuario_id = int(get_jwt_identity())
    usuario = UsuarioService.obter_por_id(usuario_id)

    return jsonify(usuario.to_dict()), 200

  except ValueError as e:
    return jsonify({'erro': str(e)}), 404
  
  except Exception:
    return jsonify({'erro': 'Erro ao buscar dados do perfil.'}), 500