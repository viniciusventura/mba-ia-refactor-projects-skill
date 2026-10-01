import logging
import sqlite3

from flask import current_app, jsonify

from database import get_db
from models import pedido_model, produto_model, usuario_model
from utils.constants import API_VERSAO

logger = logging.getLogger(__name__)


def index():
    return jsonify({
        "mensagem": "Bem-vindo à API da Loja",
        "versao": API_VERSAO,
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
        db = get_db()
        counts = {
            "produtos": produto_model.contar(db),
            "usuarios": usuario_model.contar(db),
            "pedidos": pedido_model.contar(db),
        }
    except sqlite3.Error:
        logger.exception("Health check: banco indisponível")
        return jsonify({"status": "erro", "detalhes": "Banco de dados indisponível"}), 500

    return jsonify({
        "status": "ok",
        "database": "connected",
        "counts": counts,
        "versao": API_VERSAO,
        "ambiente": current_app.config["APP_ENV"],
    }), 200
