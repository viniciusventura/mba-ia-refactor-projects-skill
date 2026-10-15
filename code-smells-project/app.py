import logging

from flask import Flask
from flask_cors import CORS

import database
from config.settings import Settings
from middlewares.error_handler import register_error_handlers
from views import register_blueprints

logger = logging.getLogger(__name__)


def create_app(settings=Settings):
    app = Flask(__name__)
    app.config.from_object(settings)
    CORS(app)
    if not settings.SECRET_KEY_DO_AMBIENTE:
        logger.warning("SECRET_KEY não definida no ambiente: usando chave aleatória (tokens expiram a cada restart)")
    database.init_app(app)
    register_blueprints(app)
    register_error_handlers(app)
    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = create_app()

if __name__ == "__main__":
    logger.info("Servidor iniciado em http://%s:%s", Settings.HOST, Settings.PORT)
    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
