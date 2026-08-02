# 实验8：探索 [slice, face] 及 [slice1, slice2] 对易子，寻找 L/R 等缺失面上的 3-cycle
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


if __name__ == "__main__":
    slices = ["MR", "ML", "MU", "MD"]
    faces = ["U", "D", "F", "B", "L", "R"]
    inv = lambda m: m + "'" if not m.endswith("'") else m[:-1]

    print("#### [slice, face] = slice face slice' face' 对中心块的作用 ####")
    comm3 = set()
    for s in slices:
        for f in faces:
            seq = [s, f, inv(s), inv(f)]
            cyc = cycle_decomp_moves(seq)
            # 分类
            lens = sorted(len(c) for c in cyc)
            mark = "3-cycle!" if (len(cyc) == 1 and lens == [3]) else ""
            print(f"[{s}, {f}] = {cyc}  {mark}")
            for c in cyc:
                if len(c) == 3:
                    comm3.add(tuple(sorted(c)))
    print(f"\n[slice,face] 产生的 3-cycle 数: {len(comm3)}")

    print("\n#### [slice1, slice2] ####")
    comm33 = set()
    for s1, s2 in itertools.permutations(slices, 2):
        seq = [s1, s2, inv(s1), inv(s2)]
        cyc = cycle_decomp_moves(seq)
        lens = sorted(len(c) for c in cyc)
        mark = "3-cycle!" if (len(cyc) == 1 and lens == [3]) else ""
        print(f"[{s1}, {s2}] = {cyc}  {mark}")
        for c in cyc:
            if len(c) == 3:
                comm33.add(tuple(sorted(c)))
    print(f"\n[slice1,slice2] 产生的 3-cycle 数: {len(comm33)}")

    # L∪R 检查
    LR = [f"{f}{r}{c}" for f in "LR" for r in [1, 2] for c in [1, 2]]
    all3 = comm3 | comm33
    lr3 = [c for c in all3 if all(x in LR for x in c)]
    print(f"\nL∪R 3-cycle 数: {len(lr3)}")
    for c in sorted(lr3):
        print("  ", c)
