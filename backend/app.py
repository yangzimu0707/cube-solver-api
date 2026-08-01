from flask import Flask, jsonify, request
from flask_cors import CORS
import kociemba
import pytwisty

app = Flask(__name__)
CORS(app)


def normalize_pytwisty_moves(raw_moves):
    """
    pytwisty 2x2 求解器会输出整体旋转 (y, y2, y', x, x2, x', z, z2, z')。
    整体旋转不能直接用 Swift 端动画演示，需要把它们展开到后续的面转动上。
    """
    # 定义每种整体旋转对后续面转动的映射
    # key: 原转动, value: 在某种整体旋转后的新转动
    # x 旋转: U->F, F->D, D->B, B->U; R->R, L->L
    # x':   U->B, B->D, D->F, F->U
    # x2:   U->D, D->U, F->B, B->F
    # y 旋转: R->B, B->L, L->F, F->R; U->U, D->D
    # y':   R->F, F->L, L->B, B->R
    # y2:   R->L, L->R, F->B, B->F
    # z 旋转: U->L, L->D, D->R, R->U; F->F, B->B
    # z':   U->R, R->D, D->L, L->U
    # z2:   U->D, D->U, R->L, L->R

    face_map = {
        'x':  {'U': 'F', 'F': 'D', 'D': 'B', 'B': 'U', 'R': 'R', 'L': 'L'},
        "x'": {'U': 'B', 'B': 'D', 'D': 'F', 'F': 'U', 'R': 'R', 'L': 'L'},
        'x2': {'U': 'D', 'D': 'U', 'F': 'B', 'B': 'F', 'R': 'R', 'L': 'L'},
        'y':  {'R': 'B', 'B': 'L', 'L': 'F', 'F': 'R', 'U': 'U', 'D': 'D'},
        "y'": {'R': 'F', 'F': 'L', 'L': 'B', 'B': 'R', 'U': 'U', 'D': 'D'},
        'y2': {'R': 'L', 'L': 'R', 'F': 'B', 'B': 'F', 'U': 'U', 'D': 'D'},
        'z':  {'U': 'L', 'L': 'D', 'D': 'R', 'R': 'U', 'F': 'F', 'B': 'B'},
        "z'": {'U': 'R', 'R': 'D', 'D': 'L', 'L': 'U', 'F': 'F', 'B': 'B'},
        'z2': {'U': 'D', 'D': 'U', 'R': 'L', 'L': 'R', 'F': 'F', 'B': 'B'},
    }

    result = []
    for move in raw_moves:
        # 如果是整体旋转，跳过，但记录状态
        if move in face_map:
            # 把之前的所有结果都按这个旋转重新映射
            new_map = face_map[move]
            result = [_remap_move(m, new_map) for m in result]
        else:
            result.append(move)
    return result


def _remap_move(move, mapping):
    if not move:
        return move
    face = move[0]
    suffix = move[1:]
    if face in mapping:
        return mapping[face] + suffix
    return move


@app.route('/')
def index():
    return jsonify({
        "status": "ok",
        "message": "Rubik's cube solver API",
        "usage": "GET /solve/<facelet-string> (24 chars for 2x2, 54 chars for 3x3)"
    })


@app.route('/solve/<cube>')
def solve(cube):
    """
    Solve a 2x2 or 3x3 Rubik's cube.
    cube: 24-character (2x2) or 54-character (3x3) facelet string
    """
    length = len(cube)

    if length == 54:
        try:
            solution = kociemba.solve(cube)
            moves = solution.split()
            return jsonify({
                "moves": moves,
                "move_count": len(moves),
                "cube": cube,
                "size": 3
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    elif length == 24:
        try:
            raw_moves = pytwisty.solve222(cube)
            moves = normalize_pytwisty_moves(raw_moves)
            return jsonify({
                "moves": moves,
                "move_count": len(moves),
                "cube": cube,
                "size": 2
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    else:
        return jsonify({
            "error": f"Cube string must be 24 (2x2) or 54 (3x3) characters, got {length}"
        }), 400


@app.route('/health')
def health():
    return jsonify({"status": "healthy"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
