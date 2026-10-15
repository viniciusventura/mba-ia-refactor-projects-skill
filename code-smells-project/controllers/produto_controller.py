import logging

from flask import g, jsonify, request

from controllers.comum import ler_json
from database import get_db
from middlewares.error_handler import NotFoundError, ValidationError
from models import produto_model

logger = logging.getLogger(__name__)


def listar_produtos():
    produtos = produto_model.listar(get_db())
    logger.info("Listando %d produtos", len(produtos))
    return jsonify({"dados": produtos, "sucesso": True}), 200


def buscar_produto(id):
    produto = produto_model.buscar_por_id(get_db(), id)
    if not produto:
        raise NotFoundError("Produto não encontrado", sucesso=False)
    return jsonify({"dados": produto, "sucesso": True}), 200


def _ler_preco(nome_param):
    valor = request.args.get(nome_param, None)
    if not valor:
        return valor
    try:
        return float(valor)
    except ValueError:
        raise ValidationError(f"Parâmetro {nome_param} inválido")


def buscar_produtos():
    termo = request.args.get("q", "")
    categoria = request.args.get("categoria", None)
    preco_min = _ler_preco("preco_min")
    preco_max = _ler_preco("preco_max")
    resultados = produto_model.buscar(get_db(), termo, categoria, preco_min, preco_max)
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200


def criar_produto():
    erro, campos = produto_model.validar(ler_json())
    if erro:
        raise ValidationError(erro)
    id = produto_model.criar(get_db(), **campos)
    logger.info("Produto criado com ID: %s", id)
    return jsonify({"dados": {"id": id}, "sucesso": True, "mensagem": "Produto criado"}), 201


def atualizar_produto(id):
    db = get_db()
    if not produto_model.buscar_por_id(db, id):
        raise NotFoundError("Produto não encontrado")
    erro, campos = produto_model.validar(ler_json())
    if erro:
        raise ValidationError(erro)
    produto_model.atualizar(db, id, **campos)
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


def deletar_produto(id):
    if not produto_model.remover(get_db(), id, removido_por=g.usuario["id"]):
        raise NotFoundError("Produto não encontrado")
    logger.info("Produto %s removido (soft delete) pelo usuário %s", id, g.usuario["id"])
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
