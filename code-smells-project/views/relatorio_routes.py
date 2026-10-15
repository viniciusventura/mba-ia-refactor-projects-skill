from flask import Blueprint

from controllers import relatorio_controller
from middlewares.auth import require_auth
from utils.constants import PAPEL_ADMIN

relatorio_bp = Blueprint("relatorios", __name__)

relatorio_bp.add_url_rule("/relatorios/vendas", "relatorio_vendas", require_auth(papel=PAPEL_ADMIN)(relatorio_controller.relatorio_vendas), methods=["GET"])
