from flask import jsonify, request

from database import get_db
from middlewares.error_handler import NotFoundError, ValidationError
from models import pedido_model
from services import notificacao_service
from utils.constants import STATUS_PEDIDO


def _inteiro(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def _validar_itens(itens):
    if not isinstance(itens, list):
        raise ValidationError("Itens inválidos")
    for item in itens:
        if not isinstance(item, dict) or not _inteiro(item.get("produto_id")):
            raise ValidationError("Item inválido: produto_id é obrigatório")
        if not _inteiro(item.get("quantidade")) or item["quantidade"] <= 0:
            raise ValidationError("Item inválido: quantidade deve ser um inteiro maior que zero")


def criar_pedido():
    dados = request.get_json(silent=True)
    if not dados:
        raise ValidationError("Dados inválidos")

    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not _inteiro(usuario_id):
        raise ValidationError("Usuario ID inválido")
    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    _validar_itens(itens)

    try:
        resultado = pedido_model.criar(get_db(), usuario_id, itens)
    except pedido_model.PedidoInvalidoError as erro:
        raise ValidationError(str(erro), sucesso=False)

    notificacao_service.notificar_pedido_criado(resultado["pedido_id"], usuario_id)
    return jsonify({"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}), 201


def listar_pedidos_usuario(usuario_id):
    return jsonify({"dados": pedido_model.listar_por_usuario(get_db(), usuario_id), "sucesso": True}), 200


def listar_todos_pedidos():
    return jsonify({"dados": pedido_model.listar_todos(get_db()), "sucesso": True}), 200


def atualizar_status_pedido(pedido_id):
    dados = request.get_json(silent=True) or {}
    novo_status = dados.get("status", "")
    if novo_status not in STATUS_PEDIDO:
        raise ValidationError("Status inválido")

    if not pedido_model.atualizar_status(get_db(), pedido_id, novo_status):
        raise NotFoundError("Pedido não encontrado")

    notificacao_service.notificar_status_pedido(pedido_id, novo_status)
    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
