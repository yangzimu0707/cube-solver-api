"""
角块求解器（4x4 / 5x5）。

方法：与 edges.py 相同的环对易子生成 3-cycle 原语，但分类条件为
"中心保持 + 边保持 + 角槽单 3-cycle"（纯角 3-cycle），然后颜色驱动贪心逐槽求解。

边块模型：每个角槽 (face, r, c) 的贴纸颜色 = 所在面颜色。
求解 = 每个角槽贴纸归位（颜色驱动，不依赖物理块身份，
因为 bigcube 模型存在拆块现象——与前端 App 行为一致）。

3-cycle 记号：定向循环 (a, b, c) 表示 a 位置的块移动到 b，b -> c，c -> a。
"""
import itertools

from bigcube import FACE_NAMES
from edges import _inv, _apply_moves_to_labeled, edge_slots, _slot_name

SLICES = ["MR", "ML", "MU", "MD"]
FACES = ["U", "D", "F", "B", "L", "R"]


def corner_slots(n):
    """所有角块面片位置 (face, r, c) 列表（每面 4 角）"""
    positions = []
    for face in range(6):
        for (r, c) in [(0, 0), (0, n - 1), (n - 1, 0), (n - 1, n - 1)]:
            positions.append((face, r, c))
    return positions


class CornerLibrary:
    """纯角块 3-cycle 原语库（中心+边保持）。key: 定向循环元组 (a,b,c)。"""

    def __init__(self, n):
        self.n = n
        self._slot_set = None
        self._by_sorted = {}

    def build(self):
        n = self.n
        slot_set = set(corner_slots(n))
        edge_set = set(edge_slots(n))
        center_set = set()
        for f in range(6):
            for r in range(1, n - 1):
                for c in range(1, n - 1):
                    center_set.add((f, r, c))
        self._slot_set = slot_set

        slices = SLICES + (["M", "E", "S"] if n >= 5 else [])
        face_variants = ["U", "U2", "U'", "D", "D2", "D'", "F", "F2", "F'",
                         "B", "B2", "B'", "L", "L2", "L'", "R", "R2", "R'"]
        wide_variants = ["TR", "TR'", "TR2", "TL", "TL'", "TL2",
                         "TU", "TU'", "TU2", "TD", "TD'", "TD2"]
        move_gens = face_variants + ["MR", "MR'", "ML", "ML'", "MU", "MU'",
                                     "MD", "MD'"] + (["M", "M'", "E", "E'", "S", "S'"] if n >= 5 else [])

        rings = []
        for s in slices:
            for f in face_variants:
                rings.append([s, f, _inv(s)])
        for w in wide_variants:
            for f in face_variants:
                rings.append([w, f, _inv(w)])

        base = {}

        def _try(comm):
            cyc, ok = self._classify(n, comm, slot_set, edge_set, center_set)
            if ok and len(cyc) == 1 and len(cyc[0]) == 3:
                c = tuple(cyc[0])
                if c not in base:
                    base[c] = comm
                    base[tuple(reversed(c))] = [_inv(m) for m in reversed(comm)]

        # 族1：环 x 单步对易子
        for ring in rings:
            for B in move_gens:
                comm = ring + [B] + [_inv(m) for m in reversed(ring)] + [_inv(B)]
                _try(comm)
                comm2 = [B] + ring + [_inv(B)] + [_inv(m) for m in reversed(ring)]
                _try(comm2)

        # 族2：环 x 环对易子
        for i, r1 in enumerate(rings):
            for r2 in rings[i + 1:]:
                comm = r1 + r2 + [_inv(m) for m in reversed(r1)] + [_inv(m) for m in reversed(r2)]
                _try(comm)

        # 迭代共轭
        conj_depth = 3
        conj_algs = face_variants + slices + wide_variants
        perms = []
        for a in conj_algs:
            cube = _apply_moves_to_labeled(n, a.split())
            perm = {}
            for (f, r, c) in corner_slots(n):
                perm[cube.get_facelet(f, r, c)] = _slot_name(f, r, c)
            perms.append((a, {v: k for k, v in perm.items()}))

        all_moves = dict(base)
        current = dict(base)
        for _ in range(conj_depth):
            nxt = {}
            for cyc, seq in current.items():
                for alg, p_inv in perms:
                    new_cyc = tuple(p_inv.get(x, x) for x in cyc)
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

    def _classify(self, n, moves, corner_set, edge_set, center_set):
        """角槽单 3-cycle 且边+中心全保持？返回 (cycles, ok)"""
        cube = _apply_moves_to_labeled(n, moves)
        mapping = {}
        for (f, r, c) in corner_set:
            mapping[_slot_name(f, r, c)] = cube.get_facelet(f, r, c)
        for (f, r, c) in edge_set:
            if cube.get_facelet(f, r, c) != _slot_name(f, r, c):
                return None, False
        for (f, r, c) in center_set:
            if cube.get_facelet(f, r, c) != _slot_name(f, r, c):
                return None, False
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
        return cycles, True

    def _add(self, cyc, moves):
        key = tuple(sorted(cyc))
        self._by_sorted.setdefault(key, []).append((tuple(cyc), moves))

    def find_cycle(self, slots, free_rule):
        """寻找一个 3-cycle：把 slots[1] 位置的块放入 slots[0]。
        第三个槽满足 free_rule。返回 (oriented_cycle, moves) 或 None。
        """
        s, p = slots
        for key, entries in self._by_sorted.items():
            if s not in key or p not in key:
                continue
            for cyc, moves in entries:
                q = [x for x in cyc if x not in (s, p)][0]
                if not free_rule(q):
                    continue
                if (cyc[0] == p and cyc[1] == s) or \
                   (cyc[1] == p and cyc[2] == s) or \
                   (cyc[2] == p and cyc[0] == s):
                    return cyc, moves
        return None


def solve_corners(cube, library=None):
    """
    求解所有角块（每个角槽贴纸 = 所在面颜色）。返回 (moves, error)。
    cube: BigCube 实例（会被修改）。
    前置条件：中心+边已解（角 3-cycle 原语保持它们）。
    """
    n = cube.size
    if library is None or library.n != n:
        library = CornerLibrary(n)
        library.build()

    slots = [_slot_name(f, r, c) for (f, r, c) in corner_slots(n)]
    solved = set()
    moves_out = []
    max_iters = 400

    for s in slots:
        fi = FACE_NAMES.index(s[0])
        r, c = int(s[1]), int(s[2])
        color = FACE_NAMES[fi]
        iters = 0
        while cube.get_facelet(fi, r, c) != color:
            iters += 1
            if iters > max_iters:
                return moves_out, f"角块求解超过迭代上限（槽{s}）"
            seq = _insert_any_candidate(cube, library, s, fi, color, solved, n)
            if seq is None:
                return moves_out, f"无法插入：槽{s}"
            cube.apply_moves(seq)
            moves_out.extend(seq)
        solved.add(s)

    return moves_out, None


def _candidate_slots(cube, color, solved, n):
    """含目标颜色的未解角槽列表"""
    out = []
    for (f, r, c) in corner_slots(n):
        name = _slot_name(f, r, c)
        if name in solved:
            continue
        if cube.get_facelet(f, r, c) == color:
            out.append(name)
    return out


def _free_rule(solved, s):
    def rule(q):
        return q is not None and q not in solved and q != s
    return rule


def _insert_any_candidate(cube, library, s, fi, color, solved, n):
    """尝试所有候选 p，把 p 处的目标色贴纸放入 s；失败返回 None。"""
    for p in _candidate_slots(cube, color, solved, n):
        seq = _find_insertion(cube, library, s, p, solved, n)
        if seq is not None:
            return seq
    return None


def _find_insertion(cube, library, s, p, solved, n):
    """把位于 p 的目标色贴纸放入 s，q 为未解槽。支持两跳 staging。"""
    rule = _free_rule(solved, s)

    hit = library.find_cycle((s, p), rule)
    if hit:
        return hit[1]

    # staging：两跳 p -> r -> s
    free_slots = []
    for name in [_slot_name(f, r, c) for (f, r, c) in corner_slots(n)]:
        if name != s and name not in solved:
            free_slots.append(name)

    for r_slot in free_slots:
        hit1 = library.find_cycle((r_slot, p), rule)
        if not hit1:
            continue
        hit2 = library.find_cycle((s, r_slot), rule)
        if not hit2:
            continue
        return hit1[1] + hit2[1]

    return None


if __name__ == "__main__":
    import sys, time
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    t0 = time.time()
    lib = CornerLibrary(n)
    lib.build()
    n_moves = sum(len(v) for v in lib._by_sorted.values())
    print(f"库构建: n={n}, 用时 {time.time()-t0:.1f}s, 条目 {n_moves}")

    all_slots = [_slot_name(f, r, c) for (f, r, c) in corner_slots(n)]
    pairs = [(s, p) for s in all_slots for p in all_slots if p != s]
    t1 = time.time()
    missing = []
    for (s, p) in pairs:
        found = False
        for key, entries in lib._by_sorted.items():
            if s not in key or p not in key:
                continue
            for cyc, moves in entries:
                if (cyc[0] == p and cyc[1] == s) or \
                   (cyc[1] == p and cyc[2] == s) or \
                   (cyc[2] == p and cyc[0] == s):
                    found = True
                    break
            if found:
                break
        if not found:
            missing.append((s, p))
    print(f"覆盖检查: {len(pairs)-len(missing)}/{len(pairs)} 缺失 {len(missing)} (用时 {time.time()-t1:.1f}s)")
    for m in missing[:10]:
        print("   ", m)
