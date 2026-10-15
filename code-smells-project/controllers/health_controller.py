import logging

from flask import current_app, jsonify

from database import get_db
from models import pedido_model, produto_model, usuario_model
from utils.constants import API_VERSION

logger = logging.getLogger(__name__)


def index():
    return jsonify({
        "mensagem": "Bem-vindo à API da Loja",
        "versao": API_VERSION,
        "endpoints": {
            "produtos": "/produtos",
            "usuarios": "/usuarios",
            "pedidos": "/pedidos",
            "login": "/login",
            "relatorios": "/relatorios/vendas",
            "health": "/health",
        },
    })


def health_check():
    try:
        db = get_db()
        counts = {
            "produtos": produto_model.contar(db),
            "usuarios": usuario_model.contar(db),
            "pedidos": pedido_model.contar(db),
        }
    except Exception:
        # health é a única rota que traduz falha de banco em resposta própria (contrato original)
        logger.exception("Health check falhou")
        return jsonify({"status": "erro", "detalhes": "Banco de dados indisponível"}), 500

    # sem configuração interna na resposta (secret_key, debug e db_path removidos: F-04)
    return jsonify({
        "status": "ok",
        "database": "connected",
        "counts": counts,
        "versao": API_VERSION,
        "ambiente": current_app.config["APP_ENV"],
    }), 200
