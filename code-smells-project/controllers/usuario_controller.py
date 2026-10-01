import logging

from flask import jsonify

from controllers.validacao import obter_json
from database import get_db
from middlewares.error_handler import NotFoundError, UnauthorizedError, ValidationError
from models import usuario_model

logger = logging.getLogger(__name__)


def listar_usuarios():
    usuarios = usuario_model.listar(get_db())
    return jsonify({"dados": usuarios, "sucesso": True}), 200


def buscar_usuario(id):
    usuario = usuario_model.buscar_por_id(get_db(), id)
    if not usuario:
        raise NotFoundError("Usuário não encontrado")
    return jsonify({"dados": usuario, "sucesso": True}), 200


def criar_usuario():
    dados = obter_json()
    if not dados:
        raise ValidationError("Dados inválidos")

    nome = dados.get("nome", "")
    email = dados.get("email", "")
    senha = dados.get("senha", "")
    if not all(isinstance(campo, str) and campo for campo in (nome, email, senha)):
        raise ValidationError("Nome, email e senha são obrigatórios")

    id = usuario_model.criar(get_db(), nome, email, senha)
    logger.info("Usuário criado: id %s", id)
    return jsonify({"dados": {"id": id}, "sucesso": True}), 201


def login():
    dados = obter_json()
    email = dados.get("email", "")
    senha = dados.get("senha", "")
    if not (isinstance(email, str) and email and isinstance(senha, str) and senha):
        raise ValidationError("Email e senha são obrigatórios")

    usuario = usuario_model.autenticar(get_db(), email, senha)
    if not usuario:
        logger.info("Login falhou")
        raise UnauthorizedError("Email ou senha inválidos", {"sucesso": False})

    logger.info("Login bem-sucedido: usuário %s", usuario["id"])
    return jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}), 200
