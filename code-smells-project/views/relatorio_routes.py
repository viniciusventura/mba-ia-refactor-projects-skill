from flask import Blueprint

from controllers import relatorio_controller
from middlewares.auth import require_auth
from utils.constants import TIPO_ADMIN

relatorio_bp = Blueprint("relatorios", __name__)
relatorio_bp.get("/relatorios/vendas")(require_auth(tipo=TIPO_ADMIN)(relatorio_controller.relatorio_vendas))
