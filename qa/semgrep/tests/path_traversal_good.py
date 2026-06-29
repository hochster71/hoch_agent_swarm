from pathlib import Path
from flask import Flask, request, abort

app = Flask(__name__)

@app.route("/api/v1/download/<path:filepath>")
def download_file(filepath):
    base_dir = Path("/app/files").resolve()
    target = (base_dir / filepath).resolve()
    # Safe checks are applied to confirm path bounds
    if not target.is_relative_to(base_dir):
        abort(403)
    return target.read_text()
