from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from schemas.avaliacao_fisica import AvaliacaoCreateSchema, AvaliacaoUpdateSchema
from services.avaliacao_fisica_service import AvaliacaoService

avaliacao_bp = Blueprint('avaliacao', __name__)


def _obter_usuario_id() -> int:
    """Extrai e converte o usuario_id do JWT com segurança."""
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return int(identity.get('id') or identity.get('sub'))
    return int(identity)


@avaliacao_bp.post('/')
@jwt_required()
def criar_avaliacao():
    """Cria uma nova avaliação física para o usuário autenticado."""
    usuario_id = _obter_usuario_id()
    dados_brutos = request.get_json() or {}

    schema = AvaliacaoCreateSchema(**dados_brutos)
    dados_validados = schema.model_dump(exclude_unset=True)

    avaliacao, erro = AvaliacaoService.criar_avaliacao(
        usuario_id, dados_validados
    )
    if erro:
        return jsonify({'erro': erro}), 400

    return (
        jsonify({
            'mensagem': 'Avaliação física criada com sucesso!',
            'dados': avaliacao.to_dict() if hasattr(avaliacao, 'to_dict') else avaliacao,
        }),
        201,
    )


@avaliacao_bp.get('/')
@jwt_required()
def listar_avaliacoes():
    """Lista todas as avaliações ativas do usuário autenticado."""
    usuario_id = _obter_usuario_id()
    apenas_ativas = request.args.get('ativas', 'true').lower() == 'true'

    avaliacoes = AvaliacaoService.listar_avaliacoes_usuario(
        usuario_id=usuario_id, apenas_ativas=apenas_ativas
    )

    # Converte cada objeto ORM retornado pelo Service em dicionário
    dados_formatados = [
        a.to_dict() if hasattr(a, 'to_dict') else a for a in avaliacoes
    ]

    return (
        jsonify({
            'total': len(dados_formatados),
            'dados': dados_formatados,
        }),
        200,
    )


@avaliacao_bp.put('/<int:avaliacao_id>')
@jwt_required()
def atualizar_avaliacao(avaliacao_id: int):
    usuario_id = _obter_usuario_id()
    dados_brutos = request.get_json() or {}

    avaliacao, erro = AvaliacaoService.atualizar_avaliacao(
        avaliacao_id=avaliacao_id,
        usuario_id=usuario_id,
        dados_validados=dados_brutos,
    )

    if erro:
        status_code = 404 if erro == 'Avaliação não encontrada ou desativada.' else 400
        return jsonify({'erros': erro}), status_code    

    return (
        jsonify({
            'mensagem': 'Avaliação física atualizada com sucesso!',
            'dados': avaliacao.to_dict() if hasattr(avaliacao, 'to_dict') else avaliacao,
        }),
        200,
    )


@avaliacao_bp.delete('/<int:avaliacao_id>')
@jwt_required()
def desativar_avaliacao(avaliacao_id: int):
    usuario_id = _obter_usuario_id()

    sucesso, erro = AvaliacaoService.desativar_avaliacao(
        avaliacao_id=avaliacao_id, usuario_id=usuario_id
    )

    if not sucesso:
        return jsonify({'erro': erro}), 404

    return jsonify({'mensagem': 'Avaliação física desativada com sucesso!'}), 200


@avaliacao_bp.put('/<int:avaliacao_id>/reativar')
@jwt_required()
def reativar_avaliacao(avaliacao_id: int):
    usuario_id = _obter_usuario_id()

    avaliacao, erro = AvaliacaoService.ativar_avaliacao(
        avaliacao_id=avaliacao_id, usuario_id=usuario_id
    )

    if erro:
        return jsonify({'erro': erro}), 404

    return (
        jsonify({
            'mensagem': 'Avaliação física reativada com sucesso!',
            'dados': avaliacao.to_dict() if hasattr(avaliacao, 'to_dict') else avaliacao,
        }),
        200,
    )