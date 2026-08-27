from datetime import date
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from models import db
from schemas.registro_diario import (
    RegistroDiarioCreateSchema,
    RegistroDiarioUpdateSchema,
)
from services.registro_diario_service import RegistroDiarioService

registro_bp = Blueprint("registros_diarios", __name__)


def _obter_usuario_id() -> int:
    """Extrai e converte o usuario_id do JWT com segurança."""
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return int(identity.get("id") or identity.get("sub"))
    return int(identity)


@registro_bp.post("/")
@jwt_required()
def criar_registro():
    """Cria um registro para o dia atual e gera o feedback."""
    json_data = request.get_json() or {}

    try:
        dados = RegistroDiarioCreateSchema(**json_data)
        usuario_id = _obter_usuario_id()

        resultado = RegistroDiarioService.criar_registro(
            usuario_id=usuario_id, dados=dados
        )

        registro = resultado["registro"]
        return (
            jsonify(
                {
                    "registro": {
                        "id": registro.id,
                        "usuario_id": registro.usuario_id,
                        "meta_id": registro.meta_id,
                        "data": registro.data.isoformat(),
                        "calorias_consumidas_kcal": registro.calorias_consumidas_kcal,
                        "proteinas_g": registro.proteinas_g,
                        "carboidratos_g": registro.carboidratos_g,
                        "gorduras_g": registro.gorduras_g,
                        "agua_consumida_ml": registro.agua_consumida_ml,
                        "exercicio_realizado": registro.exercicio_realizado,
                        "peso_registro_kg": registro.peso_registro_kg,
                        "observacoes": registro.observacoes,
                    },
                    "feedback": resultado["feedback"],
                }
            ),
            201,
        )

    except ValueError as err:
        return jsonify({"erro": str(err)}), 400


@registro_bp.get("/hoje")
@jwt_required()
def buscar_registro_hoje():
    """Recupera as métricas do dia atual para o usuário autenticado."""
    usuario_id = _obter_usuario_id()

    registro = RegistroDiarioService.buscar_por_data(
        usuario_id=usuario_id, data_consulta=date.today()
    )

    if not registro:
        return (
            jsonify({"erro": "Nenhum registro encontrado para a data de hoje."}),
            404,
        )

    return (
        jsonify(
            {
                "id": registro.id,
                "data": registro.data.isoformat(),
                "calorias_consumidas_kcal": registro.calorias_consumidas_kcal,
                "proteinas_g": registro.proteinas_g,
                "carboidratos_g": registro.carboidratos_g,
                "gorduras_g": registro.gorduras_g,
                "agua_consumida_ml": registro.agua_consumida_ml,
                "exercicio_realizado": registro.exercicio_realizado,
                "peso_registro_kg": registro.peso_registro_kg,
                "observacoes": registro.observacoes,
            }
        ),
        200,
    )


@registro_bp.get("/<int:registro_id>")
@jwt_required()
def buscar_registro_por_id(registro_id: int):
    """Busca um registro específico garantindo o escopo do usuário autenticado."""
    usuario_id = _obter_usuario_id()

    registro = RegistroDiarioService.buscar_por_id(
       usuario_id=usuario_id, registro_id=registro_id
    )

    if not registro:
        return jsonify({"erro": "Registro diário não encontrado."}), 404

    return (
        jsonify(
            {
                "id": registro.id,
                "data": registro.data.isoformat(),
                "calorias_consumidas_kcal": registro.calorias_consumidas_kcal,
                "proteinas_g": registro.proteinas_g,
                "carboidratos_g": registro.carboidratos_g,
                "gorduras_g": registro.gorduras_g,
                "agua_consumida_ml": registro.agua_consumida_ml,
                "exercicio_realizado": registro.exercicio_realizado,
                "peso_registro_kg": registro.peso_registro_kg,
                "observacoes": registro.observacoes,
            }
        ),
        200,
    )


@registro_bp.put("/<int:registro_id>")
@jwt_required()
def atualizar_registro(registro_id: int):
    """Atualiza parcialmente um registro e recalcula o feedback."""
    json_data = request.get_json() or {}

    try:
        dados = RegistroDiarioUpdateSchema(**json_data)
        usuario_id = _obter_usuario_id()

        resultado = RegistroDiarioService.atualizar_registro(
            usuario_id=usuario_id,
            registro_id=registro_id,
            dados=dados
        )

        registro = resultado["registro"]
        return (
            jsonify(
                {
                    "registro": {
                        "id": registro.id,
                        "data": registro.data.isoformat(),
                        "calorias_consumidas_kcal": registro.calorias_consumidas_kcal,
                        "proteinas_g": registro.proteinas_g,
                        "carboidratos_g": registro.carboidratos_g,
                        "gorduras_g": registro.gorduras_g,
                        "agua_consumida_ml": registro.agua_consumida_ml,
                    },
                    "feedback": resultado["feedback"],
                }
            ),
            200,
        )

    except ValueError as err:
        return jsonify({"erro": str(err)}), 404


@registro_bp.delete("/<int:registro_id>")
@jwt_required()
def deletar_registro(registro_id: int):
    """Remove o registro diário."""
    usuario_id = _obter_usuario_id()

    sucesso = RegistroDiarioService.deletar_registro(
       usuario_id=usuario_id, registro_id=registro_id
    )

    if not sucesso:
        return jsonify({"erro": "Registro diário não encontrado."}), 404

    return jsonify({"mensagem": "Registro diário foi removido com sucesso."}), 200