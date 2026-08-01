from flask import Flask, jsonify, request
from flask_cors import CORS
import kociemba

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return jsonify({
        "status": "ok",
        "message": "Kociemba cube solver API",
        "usage": "GET /solve/<54-character-facelet-string>"
    })


@app.route('/solve/<cube>')
def solve(cube):
    """
    Solve a 3x3 Rubik's cube using Kociemba algorithm.
    cube: 54-character facelet string in order U, R, F, D, L, B
    """
    if len(cube) != 54:
        return jsonify({
            "error": f"Cube string must be 54 characters, got {len(cube)}"
        }), 400

    try:
        solution = kociemba.solve(cube)
        moves = solution.split()
        return jsonify({
            "moves": moves,
            "move_count": len(moves),
            "cube": cube
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/health')
def health():
    return jsonify({"status": "healthy"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
