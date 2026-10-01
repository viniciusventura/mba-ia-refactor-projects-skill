import logging
from numbers import Number

from flask import jsonify, request

from database import get_db
from middlewares.error_handler import NotFoundError, ValidationError
from models import produto_model
from utils.constants import CATEGORIA_PADRAO, CATEGORIAS_VALIDAS, NOME_PRODUTO_MAX, NOME_PRODUTO_MIN

logger = logging.getLogger(__name__)

CAMPOS_OBRIGATORIOS = [("nome", "Nome é obrigatório"), ("preco", "Preço é obrigatório"), ("estoque", "Estoque é obrigatório")]


def _numero(valor):
    return isinstance(valor, Number) and not isinstance(valor, bool)


def _ler_produto(dados):
    """Validação comum a criação e edição (mesmas mensagens do contrato original)."""
    if not dados:
        raise ValidationError("Dados inválidos")
    for campo, mensagem in CAMPOS_OBRIGATORIOS:
        if campo not in dados:
            raise ValidationError(mensagem)

    produto = {
        "nome": dados["nome"],
        "descricao": dados.get("descricao", ""),
        "preco": dados["preco"],
        "estoque": dados["estoque"],
        "categoria": dados.get("categoria", CATEGORIA_PADRAO),
    }
    if not isinstance(produto["nome"], str):
        raise ValidationError("Nome inválido")
    if not isinstance(produto["descricao"], str):
        raise ValidationError("Descrição inválida")
    if not isinstance(produto["categoria"], str):
        raise ValidationError("Categoria inválida")
    if not _numero(produto["preco"]):
        raise ValidationError("Preço inválido")
    if not isinstance(produto["estoque"], int) or isinstance(produto["estoque"], bool):
        raise ValidationError("Estoque inválido")
    if produto["preco"] < 0:
        raise ValidationError("Preço não pode ser negativo")
    if produto["estoque"] < 0:
        raise ValidationError("Estoque não pode ser negativo")
    return produto


def _ler_preco(nome_parametro):
    valor = request.args.get(nome_parametro, None)
    if not valor:
        return valor
    try:
        return float(valor)
    except ValueError:
        raise ValidationError(nome_parametro + " inválido")


def listar_produtos():
    produtos = produto_model.listar(get_db())
    logger.info("Listando %d produtos", len(produtos))
    return jsonify({"dados": produtos, "sucesso": True}), 200


def buscar_produto(id):
    produto = produto_model.buscar_por_id(get_db(), id)
    if not produto:
        raise NotFoundError("Produto não encontrado", sucesso=False)
    return jsonify({"dados": produto, "sucesso": True}), 200


def criar_produto():
    produto = _ler_produto(request.get_json(silent=True))

    if len(produto["nome"]) < NOME_PRODUTO_MIN:
        raise ValidationError("Nome muito curto")
    if len(produto["nome"]) > NOME_PRODUTO_MAX:
        raise ValidationError("Nome muito longo")
    if produto["categoria"] not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(CATEGORIAS_VALIDAS))

    id = produto_model.criar(get_db(), **produto)
    logger.info("Produto criado com ID: %s", id)
    return jsonify({"dados": {"id": id}, "sucesso": True, "mensagem": "Produto criado"}), 201


def atualizar_produto(id):
    db = get_db()
    if not produto_model.buscar_por_id(db, id):
        raise NotFoundError("Produto não encontrado")

    produto = _ler_produto(request.get_json(silent=True))
    produto_model.atualizar(db, id, **produto)
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


def deletar_produto(id):
    if not produto_model.remover(get_db(), id):
        raise NotFoundError("Produto não encontrado")
    logger.info("Produto %s removido (soft delete)", id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200


def buscar_produtos():
    termo = request.args.get("q", "")
    categoria = request.args.get("categoria", None)
    preco_min = _ler_preco("preco_min")
    preco_max = _ler_preco("preco_max")

    resultados = produto_model.buscar(get_db(), termo, categoria, preco_min, preco_max)
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200
