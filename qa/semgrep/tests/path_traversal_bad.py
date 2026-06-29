import os
from flask import Flask, request, abort

app = Flask(__name__)

@app.route("/api/v1/download/<path:filepath>")
def download_file(filepath):
    # Matches vulnerable pattern 1: direct join and open
    target = os.path.join("/app/files", filepath)
    with open(target, "r") as f:
        return f.read()
