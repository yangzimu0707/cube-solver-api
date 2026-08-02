"""
2x2 Rubik's Cube solver using bidirectional BFS
Fast: explores from both the scrambled state and the solved state simultaneously,
plus removes redundant consecutive same-face moves.
"""

from collections import deque

# 2x2 cube: 24 stickers, 6 faces with 4 stickers each
# Order: U(0-3), F(4-7), R(8-11), D(12-15), B(16-19), L(20-23)
# Face layout:
# 0 1
# 2 3

def rotate_face_cw(state, face):
    s = list(state)
    f = face * 4
    s[f], s[f+1], s[f+2], s[f+3] = s[f+2], s[f], s[f+3], s[f+1]
    return tuple(s)

def apply_U(state):
    s = list(state)
    # Rotate U face
    s[0], s[1], s[2], s[3] = s[2], s[0], s[3], s[1]
    # Cycle top row: F->R->B->L->F
    s[4], s[5], s[8], s[9], s[16], s[17], s[20], s[21] = \
        s[8], s[9], s[16], s[17], s[20], s[21], s[4], s[5]
    return tuple(s)

def apply_D(state):
    s = list(state)
    s[12], s[13], s[14], s[15] = s[14], s[12], s[15], s[13]
    s[6], s[7], s[10], s[11], s[18], s[19], s[22], s[23] = \
        s[22], s[23], s[6], s[7], s[10], s[11], s[18], s[19]
    return tuple(s)

def apply_R(state):
    s = list(state)
    s[8], s[9], s[10], s[11] = s[10], s[8], s[11], s[9]
    s[1], s[3], s[5], s[7], s[13], s[15], s[17], s[19] = \
        s[17], s[19], s[1], s[3], s[5], s[7], s[15], s[13]
    return tuple(s)

def apply_L(state):
    s = list(state)
    s[20], s[21], s[22], s[23] = s[22], s[20], s[23], s[21]
    s[0], s[2], s[4], s[6], s[12], s[14], s[16], s[18] = \
        s[12], s[14], s[0], s[2], s[18], s[16], s[6], s[4]
    return tuple(s)

def apply_F(state):
    s = list(state)
    s[4], s[5], s[6], s[7] = s[6], s[4], s[7], s[5]
    s[2], s[3], s[8], s[10], s[12], s[13], s[21], s[23] = \
        s[21], s[23], s[2], s[3], s[8], s[10], s[13], s[12]
    return tuple(s)

def apply_B(state):
    s = list(state)
    s[16], s[17], s[18], s[19] = s[18], s[16], s[19], s[17]
    s[0], s[1], s[9], s[11], s[14], s[15], s[20], s[22] = \
        s[9], s[11], s[14], s[15], s[22], s[20], s[0], s[1]
    return tuple(s)

# (name, func, face)
MOVES = [
    ("U",  apply_U, "U"),
    ("U'", lambda s: apply_U(apply_U(apply_U(s))), "U"),
    ("D",  apply_D, "D"),
    ("D'", lambda s: apply_D(apply_D(apply_D(s))), "D"),
    ("R",  apply_R, "R"),
    ("R'", lambda s: apply_R(apply_R(apply_R(s))), "R"),
    ("L",  apply_L, "L"),
    ("L'", lambda s: apply_L(apply_L(apply_L(s))), "L"),
    ("F",  apply_F, "F"),
    ("F'", lambda s: apply_F(apply_F(apply_F(s))), "F"),
    ("B",  apply_B, "B"),
    ("B'", lambda s: apply_B(apply_B(apply_B(s))), "B"),
]

def solve_222(state_str):
    if len(state_str) != 24:
        raise ValueError(f"State string must be 24 characters, got {len(state_str)}")

    start = tuple(state_str)

    # Goal: each face uniform (colors taken from start's face colors)
    goal = tuple(
        [start[0]] * 4 + [start[4]] * 4 + [start[8]] * 4 +
        [start[12]] * 4 + [start[16]] * 4 + [start[20]] * 4
    )

    if start == goal:
        return []

    # Bidirectional BFS
    # parent: state -> (prev_state, move_name, face)
    f_parent = {start: (None, None, None)}
    b_parent = {goal: (None, None, None)}
    f_queue = deque([start])
    b_queue = deque([goal])

    def expand_one(state, parent, queue, other_parent):
        prev = parent[state]
        last_face = prev[2]
        for move_name, move_func, face in MOVES:
            if face == last_face:
                continue  # skip redundant consecutive same-face moves
            new_state = move_func(state)
            if new_state in parent:
                continue
            parent[new_state] = (state, move_name, face)
            if new_state in other_parent:
                return new_state
            queue.append(new_state)
        return None

    meeting = None

    while f_queue and b_queue:
        if len(f_queue) <= len(b_queue):
            meeting = expand_one(f_queue.popleft(), f_parent, f_queue, b_parent)
        else:
            meeting = expand_one(b_queue.popleft(), b_parent, b_queue, f_parent)
        if meeting is not None:
            break

    if meeting is None:
        return None

    # Reconstruct path: start -> meeting (forward)
    f_moves = []
    cur = meeting
    while f_parent[cur][0] is not None:
        prev, move, _ = f_parent[cur]
        f_moves.append(move)
        cur = prev
    f_moves.reverse()

    # meeting -> goal (backward)
    b_moves = []
    cur = meeting
    while b_parent[cur][0] is not None:
        prev, move, _ = b_parent[cur]
        b_moves.append(move)
        cur = prev

    return f_moves + b_moves
