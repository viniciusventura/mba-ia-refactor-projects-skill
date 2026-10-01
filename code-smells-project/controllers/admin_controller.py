import logging

from flask import jsonify

import database

logger = logging.getLogger(__name__)


def reset_database():
    database.reset_dados(database.get_db())
    logger.warning("Banco de dados resetado")
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200
