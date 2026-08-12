from flask import Flask, jsonify, request
from flask_cors import CORS
from kociemba_guard import is_valid_3x3, solve_with_timeout
from solver222 import solve_222
from solver444 import solve_444
from solver555 import solve_555
from deepseek_service import chat_with_deepseek

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return jsonify({
        "status": "ok",
        "message": "Multi-order Rubik's cube solver API",
        "usage": {
            "2x2": "GET /solve/2/<24-character-facelet-string>",
            "3x3": "GET /solve/<54-character-facelet-string>",
            "4x4": "GET /solve/4/<96-character-facelet-string>",
            "5x5": "GET /solve/5/<150-character-facelet-string>"
        }
    })


@app.route('/solve/2/<cube>')
def solve_2x2(cube):
    """
    Solve a 2x2 Rubik's cube using BFS.
    cube: 24-character facelet string in order U, F, R, D, B, L
    """
    if len(cube) != 24:
        return jsonify({
            "error": f"2x2 cube string must be 24 characters, got {len(cube)}"
        }), 400

    try:
        solution = solve_222(cube)
        if solution is None:
            return jsonify({"error": "No solution found"}), 400
        return jsonify({
            "moves": solution,
            "move_count": len(solution),
            "cube": cube
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/solve/4/<cube>')
def solve_4x4(cube):
    """
    Solve a 4x4 Rubik's cube using reduction method.
    cube: 96-character facelet string in order U, F, R, D, B, L
    """
    if len(cube) != 96:
        return jsonify({
            "error": f"4x4 cube string must be 96 characters, got {len(cube)}"
        }), 400

    try:
        solution = solve_444(cube)
        return jsonify({
            "moves": solution,
            "move_count": len(solution),
            "cube": cube
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/solve/5/<cube>')
def solve_5x5(cube):
    """
    Solve a 5x5 Rubik's cube using reduction method.
    cube: 150-character facelet string in order U, F, R, D, B, L
    """
    if len(cube) != 150:
        return jsonify({
            "error": f"5x5 cube string must be 150 characters, got {len(cube)}"
        }), 400

    try:
        solution = solve_555(cube)
        return jsonify({
            "moves": solution,
            "move_count": len(solution),
            "cube": cube
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


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

    if not is_valid_3x3(cube):
        return jsonify({
            "error": "魔方状态无效（颜色数量不正确）"
        }), 400

    try:
        solution = solve_with_timeout(cube)
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


@app.route('/ai/chat', methods=['POST'])
def ai_chat():
    """
    DeepSeek AI 教学代理接口（与魔方求解共用同一服务器）。
    body: {
        "messages": [{"role": "user"|"assistant", "content": "..."}, ...],
        "mode": "chat" | "guided",
        "cube": "魔方状态字符串（可选，chat 模式下会附带给 AI 参考）"
    }
    """
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])
    if not isinstance(messages, list) or not messages:
        return jsonify({"error": "messages 不能为空"}), 400

    mode = data.get("mode", "chat")
    if mode not in ("chat", "guided"):
        mode = "chat"
    cube = data.get("cube") or None

    try:
        reply = chat_with_deepseek(messages, mode=mode, cube=cube)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
