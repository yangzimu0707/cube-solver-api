# 测试 edges.py：中心解好后随机打乱边 -> 求解边块 -> 验证边+中心
import sys, random, time
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube, FACE_NAMES, cube_from_solved
from edges import EdgeLibrary, solve_edges, edge_slots
from centers import CenterLibrary, solve_centers

ALL_MOVES = ["U", "U'", "U2", "D", "D'", "D2", "F", "F'", "F2", "B", "B'", "B2",
             "L", "L'", "L2", "R", "R'", "R2",
             "TR", "TR'", "TR2", "TL", "TL'", "TL2", "TU", "TU'", "TU2", "TD", "TD'", "TD2",
             "MR", "MR'", "MR2", "ML", "ML'", "ML2", "MU", "MU'", "MU2", "MD", "MD'", "MD2"]


def solved_cube(n):
    return BigCube(n, cube_from_solved(n))


def random_scramble(n, length=None, seed=None):
    rng = random.Random(seed)
    moves = []
    prev = None
    for _ in range(length or (40 if n == 4 else 60)):
        m = rng.choice(ALL_MOVES)
        base = m.rstrip("'2")
        if prev and prev == base:
            continue
        prev = base
        moves.append(m)
    return moves


def edges_solved(cube):
    n = cube.size
    for (f, r, c) in edge_slots(n):
        if cube.get_facelet(f, r, c) != FACE_NAMES[f]:
            return False
    return True


def centers_solved(cube):
    n = cube.size
    for f in range(6):
        for r in range(1, n - 1):
            for c in range(1, n - 1):
                if cube.get_facelet(f, r, c) != FACE_NAMES[f]:
                    return False
    return True


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    only_edges = "--edges-only" in sys.argv

    t0 = time.time()
    lib = EdgeLibrary(n)
    lib.build()
    print(f"边库构建: n={n}, 用时 {time.time()-t0:.1f}s, 条目 {sum(len(v) for v in lib._by_sorted.values())}")

    for trial in range(trials):
        scramble = random_scramble(n, seed=seed + trial)
        cube = solved_cube(n)
        cube.apply_moves(scramble)

        if not only_edges:
            t1 = time.time()
            cmoves, cerr = solve_centers(cube)
            dt1 = time.time() - t1
            if cerr:
                print(f"Trial {trial}: 中心失败: {cerr}")
                continue

        t2 = time.time()
        emoves, eerr = solve_edges(cube, lib)
        dt2 = time.time() - t2

        if eerr:
            print(f"Trial {trial}: 边块失败: {eerr} (用时 {dt2:.1f}s)")
            continue

        eok = edges_solved(cube)
        cok = centers_solved(cube)
        status = ("✓" if eok and cok else "✗")
        detail = ""
        if not eok:
            detail += " 边未解!"
        if not cok:
            detail += " 中心被破坏!"
        print(f"Trial {trial}: 打乱 {len(scramble)} 步, 中心 {len(cmoves) if not only_edges else '-'} 步, 边 {len(emoves)} 步, "
              f"用时 {dt1 if not only_edges else 0:.1f}s+{dt2:.1f}s {status}{detail}")
        if not eok:
            bad = [f"{FACE_NAMES[f]}{r}{c}" for (f, r, c) in edge_slots(n)
                   if cube.get_facelet(f, r, c) != FACE_NAMES[f]]
            print("   错误边槽:", bad[:12])
        if not cok:
            badc = [f"{FACE_NAMES[f]}{r}{c}" for f in range(6) for r in range(1, n-1) for c in range(1, n-1)
                    if cube.get_facelet(f, r, c) != FACE_NAMES[f]]
            print("   错误中心槽:", badc[:12])


if __name__ == "__main__":
    main()
