# 实验6：搜索所有环对对易子，收集所有 3-cycle，验证 L∪R 覆盖
import sys, itertools
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube

FACE_NAMES = ["U", "D", "F", "B", "L", "R"]
n = 4


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


def compose(cycles1, cycles2):
    move1 = {}
    for c in cycles1:
        for i in range(len(c)):
            move1[c[i]] = c[(i + 1) % len(c)]
    move2 = {}
    for c in cycles2:
        for i in range(len(c)):
            move2[c[i]] = c[(i + 1) % len(c)]
    move = {}
    for k in set(move1) | set(move2):
        mid = move1.get(k, k)
        move[k] = move2.get(mid, mid)
    visited = set()
    result = []
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
            result.append(cyc)
    return result


def invert(cycles):
    return [c[::-1] for c in cycles]


if __name__ == "__main__":
    slices = ["MR", "ML", "MU", "MD"]
    faces = ["U", "D", "F", "B", "L", "R"]

    # 所有环
    rings = {}
    for s in slices:
        for f in faces:
            alg = f"{s} {f} {s}'"
            rings[(s, f)] = cycle_decomp_moves(alg.split())

    inv = lambda m: m + "'" if not m.endswith("'") else m[:-1]

    three_cycles = set()
    all_comm = []
    items = list(rings.items())
    for (s1, f1), c1 in items:
        for (s2, f2), c2 in items:
            if (s1, f1) >= (s2, f2):
                continue
            pieces1 = set(itertools.chain.from_iterable(c1))
            pieces2 = set(itertools.chain.from_iterable(c2))
            common = pieces1 & pieces2
            if len(common) not in (1, 2):
                continue
            c1_inv = invert(c1)
            c2_inv = invert(c2)
            # [p,q] = p q p' q'
            step = c1
            step = compose(step, c2)
            step = compose(step, c1_inv)
            step = compose(step, c2_inv)
            cyc = [c for c in step if len(c) > 1]
            cyc3 = [c for c in cyc if len(c) == 3]
            if len(cyc) == 1 and len(cyc3) == 1:
                three_cycles.add(tuple(sorted(cyc3[0])))
                all_comm.append((s1, f1, s2, f2, cyc3[0]))

    print(f"环对数（共享1或2点）产生的 3-cycle 数: {len(three_cycles)}")

    # L∪R 覆盖检查
    LR = [f"{f}{r}{c}" for f in "LR" for r in [1, 2] for c in [1, 2]]
    missing = []
    for s in LR:
        for p in LR:
            if p == s:
                continue
            ok = False
            for cyc in three_cycles:
                if s in cyc and p in cyc:
                    q = [x for x in cyc if x not in (s, p)][0]
                    if q in LR:
                        ok = True
                        break
            if not ok:
                missing.append((s, p))
    print(f"L∪R 缺失: {len(missing)}")
    for m in missing[:30]:
        print("  ", m)

    # 打印所有 L∪R 3-cycle
    print()
    print("L∪R 3-cycle 示例:")
    lr_cycles = [c for c in three_cycles if all(x in LR for x in c)]
    for c in sorted(lr_cycles)[:40]:
        # 找到对应算法
        for (a1, b1, a2, b2, cc) in all_comm:
            if tuple(sorted(cc)) == c:
                print(f"  {c}  <=  [{a1} {b1} {a1}', {a2} {b2} {a2}']")
                break
    print(f"\nL∪R 3-cycle 总数: {len(lr_cycles)}")
