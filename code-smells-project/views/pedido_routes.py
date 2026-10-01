from flask import Blueprint

from controllers import pedido_controller

pedido_bp = Blueprint("pedidos", __name__)
pedido_bp.post("/pedidos")(pedido_controller.criar_pedido)
pedido_bp.get("/pedidos")(pedido_controller.listar_todos_pedidos)
pedido_bp.get("/pedidos/usuario/<int:usuario_id>")(pedido_controller.listar_pedidos_usuario)
pedido_bp.put("/pedidos/<int:pedido_id>/status")(pedido_controller.atualizar_status_pedido)
