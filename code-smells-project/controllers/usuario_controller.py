import logging

from flask import jsonify

from controllers.comum import ler_json
from database import get_db
from middlewares.auth import emitir_token, exigir_dono_ou_admin
from middlewares.error_handler import NotFoundError, UnauthorizedError, ValidationError
from models import usuario_model

logger = logging.getLogger(__name__)


def listar_usuarios():
    return jsonify({"dados": usuario_model.listar(get_db()), "sucesso": True}), 200


def buscar_usuario(id):
    exigir_dono_ou_admin(id)
    usuario = usuario_model.buscar_por_id(get_db(), id)
    if not usuario:
        raise NotFoundError("Usuário não encontrado")
    return jsonify({"dados": usuario, "sucesso": True}), 200


def _texto(dados, campo):
    valor = dados.get(campo, "")
    return valor if isinstance(valor, str) else ""


def criar_usuario():
    dados = ler_json()
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")

    nome = _texto(dados, "nome")
    email = _texto(dados, "email")
    senha = _texto(dados, "senha")
    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")

    # cadastro público: o tipo é sempre o padrão (cliente), nunca vem do body
    id = usuario_model.criar(get_db(), nome, email, senha)
    logger.info("Usuário criado: id %s", id)
    return jsonify({"dados": {"id": id}, "sucesso": True}), 201


def login():
    dados = ler_json()
    if not isinstance(dados, dict):
        dados = {}
    email = _texto(dados, "email")
    senha = _texto(dados, "senha")
    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")

    usuario = usuario_model.autenticar(get_db(), email, senha)
    if not usuario:
        logger.info("Login falhou")
        raise UnauthorizedError("Email ou senha inválidos", sucesso=False)

    logger.info("Login bem-sucedido: usuário %s", usuario["id"])
    usuario["token"] = emitir_token(usuario)
    return jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}), 200
