"""Flask server für den Bildwasserzeichen-Checker."""

import os
from flask import Flask, request, jsonify, send_from_directory
from app import ImageChecker

app = Flask(__name__, static_folder='.', static_url_path='')


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze_image():
    """Accept uploaded image file → run all local checks + return results."""
    if 'file' not in request.files:
        return jsonify({'error': 'Kein Datei-Feld im Request.'}), 400

    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'Keine Datei ausgewählt.'}), 400

    # Save temp copy
    ext = os.path.splitext(f.filename)[1].lower() or '.jpg'
    tmp_name = f'temp_{os.urandom(8).hex()}{ext}'
    save_path = os.path.join(os.environ.get('UPLOAD_DIR', '/tmp'), tmp_name)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    f.save(save_path)

    try:
        checker = ImageChecker()
        result = checker.analyze(save_path)
        return jsonify(result)
    finally:
        try:
            os.remove(save_path)
        except OSError:
            pass


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5700))
    print(f'\n\U0001F9EA Wasserzeichen-Checker — http://localhost:{port}\n')
    app.run(host='0.0.0.0', port=port, debug=False)
