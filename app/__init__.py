"""Home OS & Fitness Hub — Flask application factory."""
from pathlib import Path

from flask import Flask

from config import get_config
from .extensions import db, login_manager


def create_app(config_object=None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or get_config())
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from .auth import auth_bp
    from .main import main_bp
    from .fitness import fitness_bp
    from .home_assistant import home_assistant_bp
    from .creality_k2 import creality_k2_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(fitness_bp, url_prefix="/fitness")
    app.register_blueprint(home_assistant_bp, url_prefix="/home")
    app.register_blueprint(creality_k2_bp, url_prefix="/printer")

    @app.template_filter("kg")
    def kg_filter(value):
        """Render weights without trailing .0 (87.5 -> '87.5', 100.0 -> '100')."""
        if value is None:
            return "—"
        return f"{value:g}"

    return app
