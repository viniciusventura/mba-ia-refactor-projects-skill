import logging

from flask import g, jsonify

from database import get_db
from models import admin_model

logger = logging.getLogger(__name__)


def reset_database():
    admin_model.resetar_banco(get_db())
    logger.warning("BANCO DE DADOS RESETADO pelo usuário %s", g.usuario["id"])
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200
