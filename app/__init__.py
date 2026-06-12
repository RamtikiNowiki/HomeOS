"""Home OS & Fitness Hub — Flask application factory."""
from pathlib import Path

from flask import Flask

from config import get_config
from .extensions import db, login_manager
from .units import format_num, format_weight


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

    @app.template_filter("lbs")
    def lbs_filter(value):
        return format_weight(value)

    @app.template_filter("kg")
    def kg_filter(value):
        """Backward-compatible alias — values are stored in lb."""
        return format_weight(value)

    @app.template_filter("num")
    def num_filter(value):
        return format_num(value)

    @app.context_processor
    def inject_workout_nav():
        from flask import request, url_for
        from flask_login import current_user

        if not current_user.is_authenticated:
            return {
                "has_active_workout": False,
                "active_workout": None,
                "fitness_workout_url": url_for("fitness.index"),
                "fitness_tab": None,
            }

        from .fitness.nav import fitness_tab_for_endpoint, workout_entry_url
        from .models import WorkoutSession

        active = WorkoutSession.query.filter_by(
            user_id=current_user.id, finished_at=None
        ).first()
        tab = fitness_tab_for_endpoint(request.endpoint)
        return {
            "has_active_workout": active is not None,
            "active_workout": active,
            "fitness_workout_url": workout_entry_url(active),
            "fitness_tab": tab,
        }

    return app
