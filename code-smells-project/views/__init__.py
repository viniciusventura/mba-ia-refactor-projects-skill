from views.admin_routes import admin_bp
from views.health_routes import health_bp
from views.pedido_routes import pedido_bp
from views.produto_routes import produto_bp
from views.relatorio_routes import relatorio_bp
from views.usuario_routes import usuario_bp


def register_blueprints(app):
    for blueprint in (produto_bp, usuario_bp, pedido_bp, relatorio_bp, health_bp, admin_bp):
        app.register_blueprint(blueprint)
