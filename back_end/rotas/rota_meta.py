from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import ValidationError

from schemas.meta import MetaCreateSchema, MetaUpdateSchema
from services.meta_service import MetaService
from rotas.formatadores import formatar_erros_pydantic

meta_bp = Blueprint('meta', __name__)


def _obter_usuario_id() -> int:
    """Extrai e converte o usuario_id do JWT com segurança."""
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return int(identity.get('id') or identity.get('sub'))
    return int(identity)


# ==============================================================================
# 1. CRIAR META (POST /api/metas/)
# ==============================================================================
@meta_bp.post('/')
@jwt_required()
def criar_meta():
    """Cria uma nova meta calculando métricas a partir da última avaliação física."""
    usuario_id = _obter_usuario_id()
    dados_brutos = request.get_json() or {}

    try:
        schema = MetaCreateSchema(**dados_brutos)
        dados_validados = schema.model_dump(exclude_unset=True)
    except ValidationError as e:
        return (
            jsonify({
                'erro': 'Dados inválidos na requisição',
                'detalhes': formatar_erros_pydantic(e),
            }),
            400,
        )

    meta_dict, erro = MetaService.criar_meta(usuario_id, dados_validados)

    if erro:
        return jsonify({'erro': erro}), 400

    return (
        jsonify({
            'mensagem': 'Meta criada com sucesso!',
            'dados': meta_dict,
        }),
        201,
    )


# ==============================================================================
# 2. OBTER META ATIVA DO USUÁRIO (GET /api/metas/ativa)
# ==============================================================================
@meta_bp.get('/ativa')
@jwt_required()
def obter_meta_ativa():
    """Busca a meta atualmente ativa para o usuário autenticado."""
    usuario_id = _obter_usuario_id()

    meta_dict, erro = MetaService.obter_meta_ativa(usuario_id)

    if erro:
        return jsonify({'erro': erro}), 404

    return (
        jsonify({
            'dados': meta_dict,
        }),
        200,
    )


# ==============================================================================
# 3. ATUALIZAR META (PUT /api/metas/<id>)
# ==============================================================================
@meta_bp.put('/<int:meta_id>')
@jwt_required()
def atualizar_meta(meta_id: int):
    """Atualiza pontualmente peso_alvo, objetivo ou status da meta."""
    usuario_id = _obter_usuario_id()
    dados_brutos = request.get_json() or {}

    try:
        schema = MetaUpdateSchema(**dados_brutos)
        dados_validados = schema.model_dump(exclude_unset=True)
    except ValidationError as e:
        return (
            jsonify({
                'erro': 'Dados inválidos na requisição',
                'detalhes': formatar_erros_pydantic(e),
            }),
            400,
        )

    meta_dict, erro = MetaService.atualizar_meta(
        meta_id=meta_id,
        usuario_id=usuario_id,
        dados_validados=dados_validados,
    )

    if erro:
        return jsonify({'erro': erro}), 404

    return (
        jsonify({
            'mensagem': 'Meta atualizada com sucesso!',
            'dados': meta_dict,
        }),
        200,
    )



@meta_bp.put("concluir/<int:meta_id>")
@jwt_required()
def concluir_meta(meta_id: int):
    usuario_id = get_jwt_identity()
    meta_atualizada, erro = MetaService.concluir_meta(meta_id, usuario_id)

    if erro:
        return jsonify({"erro": erro}), 400
    return jsonify({"mensagem": "Meta concluída com sucesso!", "data": meta_atualizada}), 200



@meta_bp.delete('/<int:meta_id>')
@jwt_required()
def deletar_meta(meta_id: int):
    """Exclui uma meta inativa (concluída ou cancelada)."""
    usuario_id = _obter_usuario_id()
    
    sucesso, erro = MetaService.deletar_meta(
        meta_id=meta_id, usuario_id=usuario_id
    )

    if not sucesso:
        status_code = 404 if erro == "Meta não encontrada" else 400
        return jsonify({'erro': erro}), status_code
    return jsonify({'mensagem': 'Meta excluída com sucesso!'}), 200

@meta_bp.put("cancelar/<int:meta_id>")
@jwt_required()
def cancelar_meta(meta_id: int):
    usuario_id = get_jwt_identity()
    meta_atualizada, erro = MetaService.cancelar_meta(meta_id, usuario_id)

    if erro:
        return jsonify({"erro": erro}), 400

    return jsonify({"mensagem": "Meta cancelada com sucesso!", "data": meta_atualizada}), 200


@meta_bp.get("/concluidas")
@jwt_required()
def listar_metas_concluidas():
    usuario_id = get_jwt_identity()
    metas, erro = MetaService.obter_metas_concluidas(usuario_id)

    if erro:
        return jsonify({"erro": erro}), 400

    return jsonify({"metas": metas, "total": len(metas)}), 200