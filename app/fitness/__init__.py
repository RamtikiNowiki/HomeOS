from flask import Blueprint

fitness_bp = Blueprint("fitness", __name__)

from . import routes  # noqa: E402,F401
