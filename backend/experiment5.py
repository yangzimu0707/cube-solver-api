# 实验5：验证 3-cycle 原语库 + 面转动共轭 是否足以支撑逐面贪心中心解法
import sys, itertools
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube

FACE_NAMES = ["U", "D", "F", "B", "L", "R"]
FACE_IDX = {f: i for i, f in enumerate(FACE_NAMES)}
n = 4
SLOTS = []
for f in FACE_NAMES:
    for r in [1, 2]:
        for c in [1, 2]:
            SLOTS.append(f"{f}{r}{c}")


def labeled_cube(n):
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
    return cube


def get_moves(cube, alg):
    cube.apply_moves(alg.split())
    return cube


def cycle_decomp(alg):
    cube = labeled_cube(n)
    get_moves(cube, alg)
    pos = cube.center_positions()
    mapping = {}
    for face in range(6):
        for (r, c) in pos[face]:
            src = cube.get_facelet(face, r, c)
            dst = f"{FACE_NAMES[face]}{r}{c}"
            mapping[dst] = src
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


def face_turn_permutations():
    """面转动对 SLOTS 的置换。返回 dict: turn_name -> {slot: new_slot}"""
    perms = {}
    for f in FACE_NAMES:
        for k in [1, 2, 3]:
            alg = f if k == 1 else (f + "2" if k == 2 else f + "'")
            cube = labeled_cube(n)
            get_moves(cube, alg)
            perm = {}
            for (r, c) in cube.center_positions()[FACE_IDX[f]]:
                src = cube.get_facelet(FACE_IDX[f], r, c)
                perm[src] = f"{f}{r}{c}"
            # 补充：只影响该面
            perm_full = {s: s for s in SLOTS}
            for s in SLOTS:
                if s[0] == f:
                    perm_full[s] = perm.get(s, s)
            perms[alg] = perm_full
    return perms


def apply_perm(cycle, perm):
    return tuple(perm[s] for s in cycle)


def main():
    base_algs = [
        "[MR U MR', MU B MU']", "[MR U MR', MU L MU']", "[MR D MR', MU F MU']",
        "[MR D MR', MU R MU']", "[MR F MR', MU F MU']", "[MR F MR', MU R MU']",
        "[MR B MR', MU B MU']", "[MR B MR', MU L MU']", "[ML U ML', MU B MU']",
        "[ML U ML', MU L MU']", "[ML D ML', MU F MU']", "[ML D ML', MU R MU']",
        "[ML F ML', MU F MU']", "[ML F ML', MU R MU']", "[ML B ML', MU B MU']",
        "[ML B ML', MU L MU']", "[MD F MD', MR D MR']", "[MD F MD', MR F MR']",
        "[MD F MD', ML D ML']", "[MD F MD', ML F ML']", "[MD B MD', MR U MR']",
        "[MD B MD', MR B MR']", "[MD B MD', ML U ML']", "[MD B MD', ML B ML']",
        "[MD L MD', MR U MR']", "[MD L MD', MR B MR']", "[MD L MD', ML U ML']",
        "[MD L MD', ML B ML']", "[MD R MD', MR D MR']", "[MD R MD', MR F MR']",
        "[MD R MD', ML D ML']", "[MD R MD', ML F ML']",
    ]

    # 解析 base_algs 为实际动作序列
    def resolve(alg):
        # 形式: [A, B] -> A B A' B'
        inner = alg.strip("[]")
        a, b = [x.strip() for x in inner.split(",")]
        inv = lambda m: m + "'" if not m.endswith("'") else m[:-1]
        seq = []
        for m in a.split():
            seq.append(m)
        for m in b.split():
            seq.append(m)
        for m in reversed(a.split()):
            seq.append(inv(m))
        for m in reversed(b.split()):
            seq.append(inv(m))
        return seq

    # 收集所有基础 3-cycle（含逆）
    base_cycles = set()
    for alg in base_algs:
        seq = resolve(alg)
        cyc = cycle_decomp(" ".join(seq))
        for c in cyc:
            if len(c) == 3:
                base_cycles.add(tuple(c))
                base_cycles.add(tuple(reversed(c)))
    print(f"基础 3-cycle 数量: {len(base_cycles)}")

    # 面转动共轭
    perms = face_turn_permutations()
    library = set()
    for c in base_cycles:
        library.add(tuple(sorted(c)))
        for p in perms.values():
            cc = apply_perm(c, p)
            library.add(tuple(sorted(cc)))
            library.add(tuple(sorted(reversed(cc))))
    print(f"共轭后 3-cycle 数量（无序三元组）: {len(library)}")

    # 检查：对每个目标面 T 的每个槽 s，是否存在 (s, p, q) 且 p/q 不在已解面
    solve_order = ["U", "D", "F", "B", "L", "R"]
    solved_before = {f: set() for f in solve_order}
    for i, f in enumerate(solve_order):
        solved_before[f] = set(solve_order[:i])

    def cycle_for_insert(target_face, slot):
        """寻找 3-cycle (p s q)：把 p 位置的块放入 s，且 q 不在已解面。
        返回 (p, q, cycle_sorted)。"""
        protected = solved_before[target_face]
        for c in library:
            # c 是无序三元组；要求 slot 在 c 中
            if slot not in c:
                continue
            others = [x for x in c if x != slot]
            # others 允许：目标面槽位（未解）或 非已解面槽位
            if all(x[0] not in protected for x in others):
                return others[0], others[1], c
        return None

    print()
    print("#### 逐面插入覆盖检查 ####")
    total_pairs = 0
    missing = []
    for tf in solve_order:
        protected = solved_before[tf]
        for s in SLOTS:
            if s[0] != tf:
                continue
            # 目标槽 s 需要放入一块来自任意非已解面 p 的块
            for p in SLOTS:
                if p == s:
                    continue
                if p[0] in protected:
                    continue
                total_pairs += 1
                res = cycle_for_insert(tf, s)
                if res is None:
                    missing.append((tf, s, p))
    print(f"需要覆盖的 (目标槽, 来源块位置) 组合: {total_pairs}")
    print(f"缺失: {len(missing)}")
    for m in missing[:40]:
        print("  缺失:", m)


if __name__ == "__main__":
    main()
