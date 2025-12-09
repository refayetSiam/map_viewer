import os
from flask import Flask, jsonify, render_template, send_from_directory

app = Flask(__name__)

# ───────── Paths ─────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_DIR = os.path.join(BASE_DIR, 'data', 'geojson')


def sanitize(name: str) -> str:
    """Strip extension, replace spaces and hyphens with underscores."""
    return os.path.splitext(name)[0].replace(' ', '_').replace('-', '_')


# ───────── Build layer map ─────────
GEOJSON_FILES = os.listdir(GEOJSON_DIR)
GEOJSON_MAP = {
    sanitize(f): f
    for f in GEOJSON_FILES
    if f.lower().endswith('.geojson')
}

# Default center (Okotoks, Alberta)
DEFAULT_CENTER = (-113.9817, 50.7256)
DEFAULT_ZOOM = 13


@app.route('/')
def index():
    return render_template(
        'index.html',
        center_lon=DEFAULT_CENTER[0],
        center_lat=DEFAULT_CENTER[1],
        zoom_level=DEFAULT_ZOOM
    )


@app.route('/manifest.json')
def manifest():
    geojsons = [{'id': _id, 'file': fname} for _id, fname in GEOJSON_MAP.items()]
    return jsonify({'geojsons': geojsons})


@app.route('/data/<path:filename>')
def data(filename):
    return send_from_directory(GEOJSON_DIR, filename)


if __name__ == '__main__':
    app.run(debug=True, port=8001)
