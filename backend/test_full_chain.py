# 全链路验证：随机打乱 -> 中心 -> 边(降阶) -> 角 -> is_solved
import sys, random, time
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube, FACE_NAMES, cube_from_solved
from centers import CenterLibrary, solve_centers
from edges import EdgeLibrary, solve_edges, edge_slots
from corners import CornerLibrary, solve_corners

ALL_MOVES = ["U", "U'", "U2", "D", "D'", "D2", "F", "F'", "F2", "B", "B'", "B2",
             "L", "L'", "L2", "R", "R'", "R2",
             "TR", "TR'", "TR2", "TL", "TL'", "TL2", "TU", "TU'", "TU2", "TD", "TD'", "TD2",
             "MR", "MR'", "MR2", "ML", "ML'", "ML2", "MU", "MU'", "MU2", "MD", "MD'", "MD2"]


def random_scramble(n, seed=None, length=None):
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


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    libc = CenterLibrary(n)
    libc.build()
    libe = EdgeLibrary(n)
    libe.build()
    libk = CornerLibrary(n)
    libk.build()

    n_fail = 0
    for trial in range(trials):
        scramble = random_scramble(n, seed=seed + trial)
        cube = BigCube(n, cube_from_solved(n))
        cube.apply_moves(scramble)

        cmoves, cerr = solve_centers(cube, libc)
        if cerr:
            print(f"Trial {trial}: 中心失败: {cerr}")
            n_fail += 1
            continue
        emoves, eerr = solve_edges(cube, libe)
        if eerr:
            print(f"Trial {trial}: 边失败: {eerr}")
            n_fail += 1
            continue
        kmoves, kerr = solve_corners(cube, libk)
        if kerr:
            print(f"Trial {trial}: 角失败: {kerr}")
            n_fail += 1
            continue

        ok = cube.is_solved()
        status = "✓还原" if ok else "✗未还原"
        if not ok:
            n_fail += 1
        total = len(cmoves) + len(emoves) + len(kmoves)
        print(f"Trial {trial}: 打乱{len(scramble)}步 中心{len(cmoves)} 边{len(emoves)} 角{len(kmoves)} "
              f"合计{total}步 {status}")
        if not ok:
            bad = [(FACE_NAMES[f], r, c, cube.get_facelet(f, r, c))
                   for f in range(6) for r in range(n) for c in range(n)
                   if cube.get_facelet(f, r, c) != FACE_NAMES[f]]
            print("   错误贴纸:", bad[:15])

    print(f"\n汇总: {trials} 次试验, 失败 {n_fail}")


if __name__ == "__main__":
    main()

