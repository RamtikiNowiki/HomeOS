"""PWA routes — service worker and manifest served from site root (required scope)."""
import json
from pathlib import Path

from flask import jsonify, request, send_from_directory


def register_pwa_routes(app):
    @app.route("/sw.js")
    def service_worker():
        resp = send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["Service-Worker-Allowed"] = "/"
        return resp

    @app.route("/manifest.webmanifest")
    def web_manifest():
        static_manifest = Path(app.static_folder) / "manifest.webmanifest"
        manifest = json.loads(static_manifest.read_text(encoding="utf-8"))

        base = app.config.get("PWA_CANONICAL_URL") or request.url_root.rstrip("/")
        manifest["start_url"] = f"{base}/"
        manifest["id"] = f"{base}/"
        # scope stays path-relative on this origin (required for service worker)
        manifest["scope"] = "/"

        for icon in manifest.get("icons", []):
            src = icon.get("src", "")
            if src.startswith("/"):
                icon["src"] = f"{base}{src}"

        resp = jsonify(manifest)
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp
