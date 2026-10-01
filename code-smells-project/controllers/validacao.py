"""Validação de entrada compartilhada pelos controllers."""
from flask import request

from middlewares.error_handler import ValidationError
from utils.constants import CATEGORIA_PADRAO, CATEGORIAS_VALIDAS, NOME_PRODUTO_MAX, NOME_PRODUTO_MIN


def obter_json():
    """Body JSON como dict; body ausente, malformado ou não-objeto vira 400."""
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    return dados


def eh_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def eh_inteiro(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def ler_float_query(nome):
    valor = request.args.get(nome, None)
    if not valor:
        return valor
    try:
        return float(valor)
    except ValueError:
        raise ValidationError("Parâmetro " + nome + " inválido")


def validar_produto(dados):
    """Mesma validação para criação e atualização. Devolve os campos normalizados."""
    if not dados:
        raise ValidationError("Dados inválidos")
    if "nome" not in dados:
        raise ValidationError("Nome é obrigatório")
    if "preco" not in dados:
        raise ValidationError("Preço é obrigatório")
    if "estoque" not in dados:
        raise ValidationError("Estoque é obrigatório")

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if not isinstance(nome, str):
        raise ValidationError("Nome inválido")
    if not isinstance(descricao, str):
        raise ValidationError("Descrição inválida")
    if not eh_numero(preco):
        raise ValidationError("Preço inválido")
    if not eh_numero(estoque):
        raise ValidationError("Estoque inválido")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_PRODUTO_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_PRODUTO_MAX:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(CATEGORIAS_VALIDAS))

    return nome, descricao, preco, estoque, categoria


def validar_itens_pedido(itens):
    if not isinstance(itens, list) or len(itens) == 0:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    for item in itens:
        if (
            not isinstance(item, dict)
            or not eh_inteiro(item.get("produto_id"))
            or not eh_inteiro(item.get("quantidade"))
            or item["quantidade"] <= 0
        ):
            raise ValidationError("Item inválido: produto_id e quantidade (inteiro > 0) são obrigatórios")
    return itens
