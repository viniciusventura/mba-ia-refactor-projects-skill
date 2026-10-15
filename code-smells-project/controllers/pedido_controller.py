from flask import jsonify

from controllers.comum import eh_inteiro, ler_json
from database import get_db
from middlewares.auth import exigir_dono_ou_admin
from middlewares.error_handler import NotFoundError, ValidationError
from models import pedido_model
from services import notificacao_service
from utils.constants import STATUS_PEDIDO


def _validar_itens(itens):
    if not isinstance(itens, list):
        raise ValidationError("Itens do pedido inválidos")
    for item in itens:
        if not isinstance(item, dict) or not eh_inteiro(item.get("produto_id")) or not eh_inteiro(item.get("quantidade")):
            raise ValidationError("Item de pedido inválido: produto_id e quantidade devem ser inteiros")
        if item["quantidade"] <= 0:
            raise ValidationError("Quantidade deve ser maior que zero")


def criar_pedido():
    dados = ler_json()
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")

    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not eh_inteiro(usuario_id):
        raise ValidationError("Usuario ID inválido")
    if not itens or len(itens) == 0:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    _validar_itens(itens)
    exigir_dono_ou_admin(usuario_id)

    try:
        resultado = pedido_model.criar(get_db(), usuario_id, itens)
    except pedido_model.PedidoInvalidoError as e:
        raise ValidationError(str(e), sucesso=False)

    notificacao_service.notificar_pedido_criado(resultado["pedido_id"], usuario_id)
    return jsonify({"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}), 201


def listar_pedidos_usuario(usuario_id):
    exigir_dono_ou_admin(usuario_id)
    return jsonify({"dados": pedido_model.listar(get_db(), usuario_id), "sucesso": True}), 200


def listar_todos_pedidos():
    return jsonify({"dados": pedido_model.listar(get_db()), "sucesso": True}), 200


def atualizar_status_pedido(pedido_id):
    dados = ler_json()
    novo_status = dados.get("status", "") if isinstance(dados, dict) else ""
    if novo_status not in STATUS_PEDIDO:
        raise ValidationError("Status inválido")

    if not pedido_model.atualizar_status(get_db(), pedido_id, novo_status):
        raise NotFoundError("Pedido não encontrado")

    notificacao_service.notificar_status_pedido(pedido_id, novo_status)
    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
