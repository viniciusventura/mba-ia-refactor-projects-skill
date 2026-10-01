import logging

from flask import jsonify, request

from controllers.validacao import ler_float_query, obter_json, validar_produto
from database import get_db
from middlewares.error_handler import NotFoundError
from models import produto_model

logger = logging.getLogger(__name__)


def listar_produtos():
    produtos = produto_model.listar(get_db())
    logger.info("Listando %s produtos", len(produtos))
    return jsonify({"dados": produtos, "sucesso": True}), 200


def buscar_produto(id):
    produto = produto_model.buscar_por_id(get_db(), id)
    if not produto:
        raise NotFoundError("Produto não encontrado", {"sucesso": False})
    return jsonify({"dados": produto, "sucesso": True}), 200


def criar_produto():
    nome, descricao, preco, estoque, categoria = validar_produto(obter_json())
    id = produto_model.criar(get_db(), nome, descricao, preco, estoque, categoria)
    logger.info("Produto criado com ID: %s", id)
    return jsonify({"dados": {"id": id}, "sucesso": True, "mensagem": "Produto criado"}), 201


def atualizar_produto(id):
    db = get_db()
    if not produto_model.buscar_por_id(db, id):
        raise NotFoundError("Produto não encontrado")
    nome, descricao, preco, estoque, categoria = validar_produto(obter_json())
    produto_model.atualizar(db, id, nome, descricao, preco, estoque, categoria)
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


def deletar_produto(id):
    db = get_db()
    if not produto_model.buscar_por_id(db, id):
        raise NotFoundError("Produto não encontrado")
    produto_model.deletar(db, id)
    logger.info("Produto %s deletado", id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200


def buscar_produtos():
    termo = request.args.get("q", "")
    categoria = request.args.get("categoria", None)
    preco_min = ler_float_query("preco_min")
    preco_max = ler_float_query("preco_max")

    resultados = produto_model.buscar(get_db(), termo, categoria, preco_min, preco_max)
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200
