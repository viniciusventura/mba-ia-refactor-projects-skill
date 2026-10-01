from flask import jsonify

from controllers.validacao import eh_inteiro, obter_json, validar_itens_pedido
from database import get_db
from middlewares.error_handler import NotFoundError, ValidationError
from models import pedido_model
from services import notificacao_service
from utils.constants import STATUS_PEDIDO


def criar_pedido():
    dados = obter_json()
    if not dados:
        raise ValidationError("Dados inválidos")

    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not eh_inteiro(usuario_id):
        raise ValidationError("Usuario ID inválido")
    validar_itens_pedido(itens)

    try:
        resultado = pedido_model.criar(get_db(), usuario_id, itens)
    except pedido_model.RegraPedidoError as e:
        raise ValidationError(str(e), {"sucesso": False})

    notificacao_service.notificar_pedido_criado(resultado["pedido_id"], usuario_id)
    return jsonify({
        "dados": resultado,
        "sucesso": True,
        "mensagem": "Pedido criado com sucesso"
    }), 201


def listar_pedidos_usuario(usuario_id):
    pedidos = pedido_model.listar(get_db(), usuario_id)
    return jsonify({"dados": pedidos, "sucesso": True}), 200


def listar_todos_pedidos():
    pedidos = pedido_model.listar(get_db())
    return jsonify({"dados": pedidos, "sucesso": True}), 200


def atualizar_status_pedido(pedido_id):
    dados = obter_json()
    novo_status = dados.get("status", "")
    if novo_status not in STATUS_PEDIDO:
        raise ValidationError("Status inválido")

    if not pedido_model.atualizar_status(get_db(), pedido_id, novo_status):
        raise NotFoundError("Pedido não encontrado")

    notificacao_service.notificar_status_pedido(pedido_id, novo_status)
    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
