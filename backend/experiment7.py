# 实验7：检查每个面对组合的 3-cycle 全覆盖情况（base + 逆 + 面转动共轭 + 切层共轭）
import sys, itertools
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube

FACE_NAMES = ["U", "D", "F", "B", "L", "R"]
n = 4
SLOTS = [f"{f}{r}{c}" for f in FACE_NAMES for r in [1, 2] for c in [1, 2]]


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


def cycle_decomp_moves(moves):
    cube = labeled_cube(n)
    cube.apply_moves(moves)
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


def face_slot_perm(alg):
    """面转动/切层对 SLOTS 的置换（位置映射）"""
    cube = labeled_cube(n)
    cube.apply_moves(alg.split())
    perm = {}
    for face in range(6):
        fname = FACE_NAMES[face]
        for (r, c) in cube.center_positions()[face]:
            src = cube.get_facelet(face, r, c)
            perm[src] = f"{fname}{r}{c}"
    return perm


if __name__ == "__main__":
    slices = ["MR", "ML", "MU", "MD"]
    faces = ["U", "D", "F", "B", "L", "R"]
    rings = {}
    for s in slices:
        for f in faces:
            rings[(s, f)] = cycle_decomp_moves(f"{s} {f} {s}'".split())

    inv = lambda m: m + "'" if not m.endswith("'") else m[:-1]

    # 所有共享 1 或 2 点的环对 -> 3-cycle
    base3 = set()
    items = list(rings.items())
    for (s1, f1), c1 in items:
        for (s2, f2), c2 in items:
            if (s1, f1) >= (s2, f2):
                continue
            pieces1 = set(itertools.chain.from_iterable(c1))
            pieces2 = set(itertools.chain.from_iterable(c2))
            if len(pieces1 & pieces2) not in (1, 2):
                continue
            def invc(cc):
                return [cc0[::-1] for cc0 in cc]
            def compose(a, b):
                m1 = {}
                for cc in a:
                    for i in range(len(cc)):
                        m1[cc[i]] = cc[(i + 1) % len(cc)]
                m2 = {}
                for cc in b:
                    for i in range(len(cc)):
                        m2[cc[i]] = cc[(i + 1) % len(cc)]
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
            step = compose(compose(compose(c1, c2), invc(c1)), invc(c2))
            cyc = [c for c in step if len(c) == 3]
            if len(cyc) == 1 and len(step) == 1:
                base3.add(tuple(cyc[0]))
                base3.add(tuple(cyc[0][::-1]))
    print(f"base 3-cycle 数: {len(base3)}")

    # 共轭集合：面转动 + 切层
    conj_algs = []
    for f in faces:
        conj_algs += [f, f + "2", f + "'"]
    for s in slices:
        conj_algs += [s, s + "2", s + "'"]
    perms = {a: face_slot_perm(a) for a in conj_algs}

    library = set()
    for c in base3:
        library.add(tuple(sorted(c)))
        for p in perms.values():
            library.add(tuple(sorted(p[x] for x in c)))
    print(f"共轭后 3-cycle 数: {len(library)}")

    # 面对组合全覆盖检查（排除同面来源：来源块已在目标面上时无需 3-cycle）
    print()
    print("#### 面对组合 (A,B) 覆盖检查（仅跨面来源） ####")
    for a, b in itertools.combinations(FACE_NAMES, 2):
        pair_slots = [s for s in SLOTS if s[0] in (a, b)]
        missing = []
        for s in pair_slots:
            for p in pair_slots:
                if p == s or p[0] == s[0]:
                    continue  # 同面来源不需要处理
                ok = False
                for cyc in library:
                    if s in cyc and p in cyc:
                        q = [x for x in cyc if x not in (s, p)][0]
                        if q in pair_slots:
                            ok = True
                            break
                if not ok:
                    missing.append((s, p))
        status = "全覆盖" if not missing else f"缺失 {len(missing)}"
        print(f"  ({a},{b}): {status}")
        if missing:
            print(f"    示例缺失: {missing[:6]}")
