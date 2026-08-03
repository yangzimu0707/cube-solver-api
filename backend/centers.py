"""
中心块求解器（4x4 / 5x5）。

方法：逐面逐槽贪心，使用经验证的 3-cycle 原语（换位子环的对易子 + 面转动/切层共轭），
必要时使用两跳中转（staging）。

3-cycle 记号：定向循环 (a, b, c) 表示 a 位置的块移动到 b，b -> c，c -> a。
要把 p 位置的块放入 s：使用定向循环 (p, s, q)（p->s）或 (q, p, s)（q->p->s）。

原语库对 4x4 和 5x5 通用生成（环的结构由 size 决定）。
"""
import itertools

from bigcube import (
    BigCube, UP, DOWN, FRONT, BACK, LEFT, RIGHT, FACE_NAMES,
)

# 面的目标颜色：面字符本身（U面=白色'U'，D面=黄色'D'，F面='F'，B面='B'，L面='L'，R面='R'）
TARGET_COLOR = {UP: "U", DOWN: "D", FRONT: "F", BACK: "B", LEFT: "L", RIGHT: "R"}

# 求解顺序：前 4 面严格贪心（U, F, D, R），最后两面对 (B, L) 联合求解。
# 依据（experiment14/15）：
# - F 面在 B 已解时最后槽无覆盖，B 面在 F 已解时同理 → F/B 不能都在严格阶段；
# - 最后两面对必须联合（最后一面无自由槽可作 q）；
# - (B,L) 联合对全覆盖（含 staging）。
SOLVE_ORDER = [UP, FRONT, DOWN, RIGHT, BACK, LEFT]

SLICES = ["MR", "ML", "MU", "MD"]
FACES = ["U", "D", "F", "B", "L", "R"]


def _inv(move):
    if move.endswith("'"):
        return move[:-1]
    if move.endswith("2"):
        return move
    return move + "'"


def _apply_moves_to_labeled(n, moves):
    cube = BigCube.__new__(BigCube)
    cube.size = n
    names = "UFRDBL"
    input_to_internal = {"U": 0, "F": 2, "R": 5, "D": 1, "B": 3, "L": 4}
    facelets = [None] * (6 * n * n)
    for i, f in enumerate(names):
        for r in range(n):
            for c in range(n):
                facelets[input_to_internal[f] * n * n + r * n + c] = f"{f}{r}{c}"
    cube.facelets = facelets
    cube.apply_moves(moves)
    return cube


def _center_slots(n):
    """返回 6 个面各自的中心槽位置列表（槽名 f{r}{c}）"""
    rows = range(1, n - 1)
    slots = {}
    for fi, fname in enumerate(FACE_NAMES):
        slots[fi] = [f"{fname}{r}{c}" for r in rows for c in rows]
    return slots


def _cycle_decomp(moves, n, slot_names):
    """对标签魔方应用 moves，返回中心槽上的块移动循环列表（piece 移动方向）"""
    cube = _apply_moves_to_labeled(n, moves)
    mapping = {}
    for fi, fname in enumerate(FACE_NAMES):
        for (r, c) in cube.center_positions()[fi]:
            src = cube.get_facelet(fi, r, c)
            mapping[f"{fname}{r}{c}"] = src
    move = {}
    for dst, src in mapping.items():
        move[src] = dst
    visited = set()
    cycles = []
    for start in move:
        if start in visited:
            continue
        cur = start
        cyc = []
        while cur not in visited:
            visited.add(cur)
            cyc.append(cur)
            cur = move[cur]
        if len(cyc) > 1:
            cycles.append(cyc)
    return cycles


def _compose(cycles1, cycles2):
    m1 = {}
    for c in cycles1:
        for i in range(len(c)):
            m1[c[i]] = c[(i + 1) % len(c)]
    m2 = {}
    for c in cycles2:
        for i in range(len(c)):
            m2[c[i]] = c[(i + 1) % len(c)]
    mm = {}
    for k in set(m1) | set(m2):
        mid = m1.get(k, k)
        mm[k] = m2.get(mid, mid)
    res = []
    seen = set()
    for start in mm:
        if start in seen:
            continue
        cur = start
        cyc = []
        while cur not in seen:
            seen.add(cur)
            cyc.append(cur)
            cur = mm[cur]
        if len(cyc) > 1:
            res.append(cyc)
    return res


def _permutation_for(alg, n, slot_names):
    """面转动/切层对中心槽的置换（位置映射 dict: slot -> new slot）"""
    cube = _apply_moves_to_labeled(n, alg.split())
    perm = {}
    for fi, fname in enumerate(FACE_NAMES):
        for (r, c) in cube.center_positions()[fi]:
            src = cube.get_facelet(fi, r, c)
            perm[src] = f"{fname}{r}{c}"
    return perm


class CenterLibrary:
    """3-cycle 原语库。key: 定向循环元组 (a,b,c)；value: 动作序列。"""

    def __init__(self, n):
        self.n = n
        self._slot_names = None
        self._by_sorted = {}  # sorted triple -> [(oriented_cycle, moves)]

    @property
    def slot_names(self):
        if self._slot_names is None:
            names = []
            for fname in FACE_NAMES:
                for r in range(1, self.n - 1):
                    for c in range(1, self.n - 1):
                        names.append(f"{fname}{r}{c}")
            self._slot_names = names
        return self._slot_names

    def build(self, conj_depth=None):
        n = self.n
        slot_names = set(self.slot_names)

        # 切层集合：5x5 及以上才有真正的中间层 M/E/S（n//2 层），加入以丰富原语
        slices = SLICES + (["M", "E", "S"] if n >= 5 else [])

        # 1. 所有环 slice face slice'
        rings = {}
        for s in slices:
            for f in FACES:
                rings[(s, f)] = [s, f, _inv(s)]

        # 2. 环对共享 1 或 2 点时取对易子 [p, q] = p q p' q'，
        #    实际应用到标签魔方验证是否为单个 3-cycle
        #    注意：p = s f s' 的逆是 s f' s'（保持夹层结构）
        base_moves = {}  # oriented 3-cycle tuple -> 动作序列
        items = list(rings.items())
        for (s1, f1), p in items:
            for (s2, f2), q in items:
                if (s1, f1) >= (s2, f2):
                    continue
                p_inv = [p[0], _inv(p[1]), p[2]]
                q_inv = [q[0], _inv(q[1]), q[2]]
                comm = p + q + p_inv + q_inv
                cyc = _cycle_decomp(comm, n, slot_names)
                if len(cyc) == 1 and len(cyc[0]) == 3:
                    c = cyc[0]
                    base_moves[tuple(c)] = comm
                    base_moves[tuple(c[::-1])] = [_inv(m) for m in reversed(comm)]

        # 3. 迭代共轭：单个 3-cycle 的共轭仍是单个 3-cycle（中心槽置换），
        #    无需逐条立方体验证。共轭轮数 5x5 需要更多。
        conj_depth = 3 if n >= 5 else 1
        if conj_depth is None:
            conj_depth = 3 if n >= 5 else 1
        conj_algs = []
        for f in FACES:
            conj_algs += [f, f + "2", f + "'"]
        for s in slices:
            conj_algs += [s, s + "2", s + "'"]
        perms = [(a, _permutation_for(a, n, slot_names)) for a in conj_algs]
        # 共轭方向：实际效果为 σ⁻¹τσ，故新循环用逆置换映射
        perms = [(a, {v: k for k, v in p.items()}) for a, p in perms]

        all_moves = dict(base_moves)
        current = dict(base_moves)
        for _ in range(conj_depth):
            nxt = {}
            for cyc, seq in current.items():
                for alg, p_inv in perms:
                    new_cyc = tuple(p_inv[x] for x in cyc)
                    if new_cyc in all_moves:
                        continue
                    all_moves[new_cyc] = [alg] + seq + [_inv(alg)]
                    nxt[new_cyc] = all_moves[new_cyc]
            current = nxt
            if not current:
                break

        self._by_sorted = {}
        for cyc, seq in all_moves.items():
            self._add(cyc, seq)

    def _add(self, cyc, moves):
        if None in cyc:
            return
        key = tuple(sorted(cyc))
        self._by_sorted.setdefault(key, []).append((tuple(cyc), moves))

    def find_cycle(self, slots, must_include, free_rule):
        """寻找一个 3-cycle：把 slots[1] 位置的块放入 slots[0]。
        要求第三个槽满足 free_rule。
        返回 (oriented_cycle, moves) 或 None。
        """
        s, p = slots
        for key, entries in self._by_sorted.items():
            if s not in key or p not in key:
                continue
            for cyc, moves in entries:
                q = [x for x in cyc if x not in (s, p)][0]
                if not free_rule(q):
                    continue
                # 需要 piece p -> s：定向循环中 p 后面紧跟 s（含循环回绕）
                # (p, s, q) / (q, p, s) / (s, q, p)
                if (cyc[0] == p and cyc[1] == s) or \
                   (cyc[1] == p and cyc[2] == s) or \
                   (cyc[2] == p and cyc[0] == s):
                    return cyc, moves
        return None


def solve_centers(cube, library=None):
    """
    求解所有中心块。返回 (moves, error)。
    cube: BigCube 实例（会被修改，应用求解动作）。

    策略（experiment14/15 验证）：
    - 阶段1：严格贪心逐面求解前 4 个面（U, F, D, R）：
      q 不能来自已解面，也不能扰动目标面已填槽。
    - 阶段2：最后两面对（B, L）联合互扰求解：
      q 可来自两面对任意槽位，直到两面对全部完成。
    """
    n = cube.size
    if library is None or library.n != n:
        library = CenterLibrary(n)
        library.build()

    solved_faces = set()
    solved_names = set()
    moves_out = []
    max_iters = 400

    # 阶段1：严格贪心（q 不能扰动目标面已填槽）
    for target_face in SOLVE_ORDER[:4]:
        color = TARGET_COLOR[target_face]
        tf_name = FACE_NAMES[target_face]
        free_rule = _make_free_rule(solved_names, tf_name, cube)
        iters = 0
        while True:
            iters += 1
            if iters > max_iters:
                return moves_out, "中心求解超过迭代上限（可能陷入循环）"
            s = _find_unfilled_slot(cube, target_face, color, n)
            if s is None:
                break
            seq = _insert_any_candidate(
                cube, library, s, target_face, color,
                solved_faces, None, free_rule, n)
            if seq is None:
                return moves_out, f"无法插入：面{tf_name} 槽{s}"
            cube.apply_moves(seq)
            moves_out.extend(seq)
        solved_faces.add(target_face)
        solved_names.add(tf_name)

    # 阶段2：联合求解最后两面对（B, L）
    # 用 BFS 在"哪些槽含目标色块"的掩码状态空间上搜索（最多 2^8 个状态），
    # 动作 = 库中完全位于联合面对内的 3-cycle。BFS 保证找到解（若可达），
    # 且不受贪心"双对换无法推进"与奇偶性问题的困扰。
    seq = _solve_joint(cube, library, SOLVE_ORDER[4:], n)
    if seq is None:
        return moves_out, "联合阶段无法求解（库覆盖不足）"
    cube.apply_moves(seq)
    moves_out.extend(seq)

    return moves_out, None


def _solve_joint(cube, library, joint_faces, n):
    """用 BFS 求解最后两面对的中心。

    状态：联合面对内哪些槽放置第一个面对的颜色块（掩码，4x4 最多 2^8 种，5x5 最多 2^18 种）。
    动作：库中三个槽都位于联合面对内的定向 3-cycle（piece 位置映射）。
    返回动作序列；若不可达返回 None。不修改 cube。
    """
    joint_names = [FACE_NAMES[f] for f in joint_faces]
    primary = joint_faces[0]
    primary_color = TARGET_COLOR[primary]
    joint_slots = [
        f"{fname}{r}{c}"
        for fname in joint_names
        for r in range(1, n - 1) for c in range(1, n - 1)
    ]
    idx = {s: i for i, s in enumerate(joint_slots)}
    nbits = len(joint_slots)  # 4x4: 8, 5x5: 18

    name_to_idx = {name: fi for fi, name in enumerate(FACE_NAMES)}

    def current_mask():
        m = 0
        for s, i in idx.items():
            fi = name_to_idx[s[0]]
            if cube.get_facelet(fi, int(s[1]), int(s[2])) == primary_color:
                m |= (1 << i)
        return m

    target_mask = 0
    for s, i in idx.items():
        if s[0] == joint_names[0]:
            target_mask |= (1 << i)

    # 收集动作：库内完全位于联合面对内的定向 3-cycle
    moves = []  # (piece_pos_map, seq, cyc)
    seen = set()
    for key, entries in library._by_sorted.items():
        for cyc, seq in entries:
            if cyc in seen:
                continue
            seen.add(cyc)
            if all(x in idx for x in cyc):
                f = {}
                for j in range(3):
                    f[idx[cyc[j]]] = idx[cyc[(j + 1) % 3]]
                moves.append((f, seq, cyc))

    start = current_mask()
    if start == target_mask:
        return []

    # BFS
    from collections import deque
    dist = {start: 0}
    parent = {}  # mask -> (prev_mask, move_index)
    q = deque([start])
    found = None
    while q:
        m = q.popleft()
        if m == target_mask:
            found = m
            break
        for mi, (f, seq, cyc) in enumerate(moves):
            m2 = 0
            for i in range(nbits):
                if (m >> i) & 1:
                    m2 |= (1 << f.get(i, i))
            if m2 not in dist:
                dist[m2] = dist[m] + 1
                parent[m2] = (m, mi)
                q.append(m2)
                if m2 == target_mask:
                    found = m2
                    q.clear()
                    break

    if found is None:
        return None

    # 回溯重建
    path = []
    m = found
    while m != start:
        prev, mi = parent[m]
        path.append(moves[mi][1])
        m = prev
    path.reverse()
    result = []
    for seq in path:
        result.extend(seq)
    return result


def _make_free_rule(solved_names, target_name, cube):
    """生成 free_rule：
    - q 不能在已解面；
    - 若 target_name 给定（严格贪心），q 在该面时必须是未填槽；
    - 否则（联合阶段）q 可在任何未解面槽位。
    """
    name_to_idx = {name: i for i, name in enumerate(FACE_NAMES)}

    def rule(q):
        if q is None:
            return False
        if q[0] in solved_names:
            return False
        if target_name is not None and q[0] == target_name:
            fi = name_to_idx[target_name]
            r, c = int(q[1]), int(q[2])
            if cube.get_facelet(fi, r, c) == TARGET_COLOR[fi]:
                return False  # 已填，不可扰动
        return True
    return rule


def _candidate_pieces(cube, color, target_face, solved_faces, joint_idx, n):
    """列出所有可作为插入源的目标色块槽位。
    范围：非目标面、非已解面；若 joint_idx 给定则限于这些面。
    """
    out = []
    for fi, fname in enumerate(FACE_NAMES):
        if fi == target_face or fi in solved_faces:
            continue
        if joint_idx is not None and fi not in joint_idx:
            continue
        for r in range(1, n - 1):
            for c in range(1, n - 1):
                if cube.get_facelet(fi, r, c) == color:
                    out.append(f"{fname}{r}{c}")
    return out


def _insert_any_candidate(cube, library, s, target_face, color,
                          solved_faces, joint_idx, free_rule, n):
    """尝试所有候选 p，找到能插入 s 的动作序列；失败返回 None。"""
    solved_names = {FACE_NAMES[f] for f in solved_faces}
    for p in _candidate_pieces(cube, color, target_face, solved_faces, joint_idx, n):
        seq = _find_insertion(cube, library, s, p, free_rule, solved_names)
        if seq is not None:
            return seq
    return None


def _find_unfilled_slot(cube, face, color, n):
    for r in range(1, n - 1):
        for c in range(1, n - 1):
            if cube.get_facelet(face, r, c) != color:
                return f"{FACE_NAMES[face]}{r}{c}"
    return None


def _find_chain(cube, library, s, p, free_rule, solved_names):
    """邻位链 fallback：s 无法直接从 p 接收 C 时，
    先用已填槽 q 的 C 填 s（q 被扰动），再用 p 的 C 回填 q。
    两步都是库内 3-cycle，q 最终恢复，不产生永久破坏。
    q 遍历所有当前含 C 的槽（未解面槽 + 目标面已填槽）。
    """
    n = library.n
    # 目标面颜色
    name_to_idx = {name: i for i, name in enumerate(FACE_NAMES)}
    target_face_name = s[0]
    color = TARGET_COLOR[name_to_idx[target_face_name]]

    # 所有含 C 的槽（可作 q），排除 s 与 p
    q_candidates = []
    for fi, fname in enumerate(FACE_NAMES):
        for r in range(1, n - 1):
            for c in range(1, n - 1):
                q = f"{fname}{r}{c}"
                if q in (s, p):
                    continue
                if cube.get_facelet(fi, r, c) == color:
                    q_candidates.append(q)

    for q in q_candidates:
        hit_a = library.find_cycle((s, q), None, free_rule)
        if not hit_a:
            continue
        hit_b = library.find_cycle((q, p), None, free_rule)
        if not hit_b:
            continue
        seq = hit_a[1] + hit_b[1]
        # 模拟验证：s 与 q 都填好 C，且已解面未被破坏
        if _chain_verify(cube, seq, s, q, color, solved_names):
            return seq
    return None


def _chain_verify(cube, seq, s, q, color, solved_names):
    """模拟 seq，验证 s、q 最终填 C，且已解面全部保持原样。
    未解面内的已归位槽允许被牺牲（后续阶段会重新处理）。返回 True/False。"""
    n = cube.size
    sim = BigCube(n, cube.serialize())
    sim.apply_moves(seq)
    name_to_idx = {name: i for i, name in enumerate(FACE_NAMES)}
    # s、q 检查
    if sim.get_facelet(name_to_idx[s[0]], int(s[1]), int(s[2])) != color:
        return False
    if sim.get_facelet(name_to_idx[q[0]], int(q[1]), int(q[2])) != color:
        return False
    # 已解面必须原样
    for name in solved_names:
        fi = name_to_idx[name]
        for r in range(1, n - 1):
            for c in range(1, n - 1):
                if sim.get_facelet(fi, r, c) != cube.get_facelet(fi, r, c):
                    return False
    return True


def _find_insertion(cube, library, s, p, free_rule, solved_names):
    """找到把 p 位置的块放入 s 的动作序列（直接、staging 或邻位链）。"""
    n = library.n

    # 直接
    hit = library.find_cycle((s, p), None, free_rule)
    if hit:
        return hit[1]

    # staging：两跳 p -> r -> s
    free_slots = []
    for fname in FACE_NAMES:
        for r in range(1, n - 1):
            for c in range(1, n - 1):
                q = f"{fname}{r}{c}"
                if q != s and free_rule(q):
                    free_slots.append(q)

    for r_slot in free_slots:
        hit1 = library.find_cycle((r_slot, p), None, free_rule)
        if not hit1:
            continue
        hit2 = library.find_cycle((s, r_slot), None, free_rule)
        if not hit2:
            continue
        return hit1[1] + hit2[1]

    # 邻位链：s <- q（已填 C），q <- p
    return _find_chain(cube, library, s, p, free_rule, solved_names)
