from flask import Blueprint

from controllers import produto_controller
from middlewares.auth import require_auth
from utils.constants import TIPO_ADMIN

produto_bp = Blueprint("produtos", __name__)
produto_bp.get("/produtos")(produto_controller.listar_produtos)
produto_bp.get("/produtos/busca")(produto_controller.buscar_produtos)
produto_bp.get("/produtos/<int:id>")(produto_controller.buscar_produto)
produto_bp.post("/produtos")(produto_controller.criar_produto)
produto_bp.put("/produtos/<int:id>")(produto_controller.atualizar_produto)
produto_bp.delete("/produtos/<int:id>")(require_auth(tipo=TIPO_ADMIN)(produto_controller.deletar_produto))
