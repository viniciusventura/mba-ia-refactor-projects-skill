import logging
import sqlite3

from flask import current_app, jsonify

from database import get_db
from models import sistema_model
from utils.constants import VERSAO_API

logger = logging.getLogger(__name__)


def index():
    return jsonify({
        "mensagem": "Bem-vindo à API da Loja",
        "versao": VERSAO_API,
        "endpoints": {
            "produtos": "/produtos",
            "usuarios": "/usuarios",
            "pedidos": "/pedidos",
            "login": "/login",
            "relatorios": "/relatorios/vendas",
            "health": "/health"
        }
    })


def health_check():
    try:
        counts = sistema_model.contar_registros(get_db())
    except sqlite3.Error:
        logger.exception("Health check: falha ao acessar o banco")
        return jsonify({"status": "erro", "detalhes": "Falha ao acessar o banco de dados"}), 500

    # Sem segredo nem configuração interna na resposta.
    return jsonify({
        "status": "ok",
        "database": "connected",
        "counts": counts,
        "versao": VERSAO_API,
        "ambiente": current_app.config["AMBIENTE"]
    }), 200


def reset_database():
    sistema_model.limpar_tabelas(get_db())
    logger.warning("Banco de dados resetado")
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200
