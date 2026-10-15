from flask import jsonify

from database import get_db
from models import relatorio_model


def relatorio_vendas():
    return jsonify({"dados": relatorio_model.relatorio_vendas(get_db()), "sucesso": True}), 200
