"""
2x2 Rubik's Cube solver using bidirectional BFS.

状态语义与 bigcube.py / 前端 CubeModel.swift 完全一致：
- 24 贴纸，面顺序 U, F, R, D, B, L，每面行优先
- 动作置换表由 bigcube 刚体转动预计算生成，保证与前端 3D 动画语义一致

Fast: bidirectional BFS + 跳过相邻同面连续动作。
"""

from collections import deque

from bigcube import BigCube

# 2x2 基本动作（面转动）
_BASIC_MOVES = ["U", "U'", "D", "D'", "R", "R'", "L", "L'", "F", "F'", "B", "B'"]


def _build_perms():
    """由 bigcube 计算 12 个基本动作对 24 个贴纸位置的置换。

    perm[m][i] = 动作 m 执行前的位置，该位置的贴纸执行后落在位置 i。
    应用方式：new_state[i] = old_state[perm[m][i]]。
    """
    labels = "".join(chr(65 + i) for i in range(24))
    perms = {}
    for m in _BASIC_MOVES:
        c = BigCube(2, labels)
        c.apply_moves([m])
        s = c.serialize()
        perms[m] = tuple(labels.index(ch) for ch in s)
    return perms


PERMS = _build_perms()

# 目标 = 绝对已解状态（前端 toCubeString 使用固定颜色方案：
# U=白, F=红, R=蓝, D=黄, B=橙, L=绿，面顺序 U,F,R,D,B,L）
SOLVED = tuple("UUUUFFFFRRRRDDDDBBBBLLLL")

# 防止不可解输入时 BFS 遍历全部 367 万个状态导致内存溢出
# （Render 免费版内存限制 512MB）。正常可解状态在双向 BFS 相遇前
# 访问的状态数远小于此值。
MAX_VISITED = 300_000


def _apply(state, move_name):
    perm = PERMS[move_name]
    return tuple(state[i] for i in perm)


def solve_222(state_str):
    if len(state_str) != 24:
        raise ValueError(f"State string must be 24 characters, got {len(state_str)}")

    start = tuple(state_str)

    if start == SOLVED:
        return []

    goal = SOLVED

    # Bidirectional BFS
    # parent: state -> (prev_state, move_name, face)
    f_parent = {start: (None, None, None)}
    b_parent = {goal: (None, None, None)}
    f_queue = deque([start])
    b_queue = deque([goal])

    def expand_one(state, parent, queue, other_parent):
        prev = parent[state]
        last_face = prev[2]
        for move_name in _BASIC_MOVES:
            if move_name[0] == last_face:
                continue  # skip redundant consecutive same-face moves
            new_state = _apply(state, move_name)
            if new_state in parent:
                continue
            parent[new_state] = (state, move_name, move_name[0])
            if new_state in other_parent:
                return new_state
            queue.append(new_state)
        return None

    meeting = None

    while f_queue and b_queue:
        # 状态数超过预算：输入可能是不可解状态，放弃搜索避免内存溢出
        if len(f_parent) + len(b_parent) > MAX_VISITED:
            return None
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
    # b_parent[child] = (parent, move)，move(parent)=child，故从 meeting 上溯
    # 收集到的逆序列 [inv(m_k),...,inv(m_1)] 恰为 meeting->goal 路径。
    b_moves = []
    cur = meeting
    while b_parent[cur][0] is not None:
        prev, move, _ = b_parent[cur]
        b_moves.append(move[:-1] if move.endswith("'") else move + "'")
        cur = prev

    return f_moves + b_moves
