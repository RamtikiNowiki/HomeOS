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

    from .pwa import register_pwa_routes
    register_pwa_routes(app)

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

    def _px_theme() -> str:
        from flask_login import current_user
        accent = getattr(current_user, "accent", None) if current_user else None
        return "pink" if accent == "pink" else "blue"

    @app.template_filter("ex_icon")
    def ex_icon_filter(exercise):
        """Static path to the themed pixel icon for an exercise (object or name)."""
        from .fitness.catalog import icon_slug_for_exercise
        name = getattr(exercise, "name", None) or str(exercise)
        group = getattr(exercise, "muscle_group", None)
        return f"img/px/{_px_theme()}/{icon_slug_for_exercise(name, group)}.png"

    @app.template_filter("ex_display")
    def ex_display_filter(exercise):
        from .fitness.catalog import display_name_for_exercise
        name = getattr(exercise, "name", None) or str(exercise)
        return display_name_for_exercise(name)

    @app.template_filter("ex_beginner")
    def ex_beginner_filter(exercise):
        from .fitness.catalog import is_beginner_exercise
        name = getattr(exercise, "name", None) or str(exercise)
        return is_beginner_exercise(name)

    @app.template_filter("ex_search")
    def ex_search_filter(exercise):
        from .fitness.catalog import aliases_for_exercise, display_name_for_exercise
        name = getattr(exercise, "name", None) or str(exercise)
        parts = [name.lower(), display_name_for_exercise(name).lower()]
        parts.extend(a.lower() for a in aliases_for_exercise(name))
        mg = getattr(exercise, "muscle_group", None)
        if mg:
            parts.append(mg.lower())
        return " ".join(parts)

    @app.context_processor
    def inject_px_theme():
        from flask_login import current_user
        accent = getattr(current_user, "accent", None) if current_user.is_authenticated else None
        if accent == "pink":
            theme_meta = {"theme_color_light": "#fdf2f8", "theme_color_dark": "#130c18", "default_theme": "light"}
        elif accent == "indigo":
            theme_meta = {"theme_color_light": "#eff6ff", "theme_color_dark": "#070b16", "default_theme": "dark"}
        else:
            theme_meta = {"theme_color_light": "#f4f6fb", "theme_color_dark": "#0b0d16", "default_theme": "dark"}
        return {"px_theme": _px_theme(), **theme_meta}

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
                "user_prefs": {},
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
            "user_prefs": {
                **{"default_rest_seconds": 90, "rest_sound": False, "pr_sound": False, "seasonal_bg": True},
                **current_user.get_preferences(),
            },
        }

    return app
