from flask import Blueprint

from controllers import health_controller

health_bp = Blueprint('health', __name__)

health_bp.get('/health')(health_controller.health)
health_bp.get('/')(health_controller.index)
