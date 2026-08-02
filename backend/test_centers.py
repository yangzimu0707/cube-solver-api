# 测试 centers.py：随机打乱 4x4 / 5x5 -> 求解中心 -> 验证
import sys, random, time
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube, FACE_NAMES
from centers import CenterLibrary, solve_centers

ALL_MOVES = ["U", "U'", "U2", "D", "D'", "D2", "F", "F'", "F2", "B", "B'", "B2",
             "L", "L'", "L2", "R", "R'", "R2",
             "TR", "TR'", "TR2", "TL", "TL'", "TL2", "TU", "TU'", "TU2", "TD", "TD'", "TD2",
             "MR", "MR'", "MR2", "ML", "ML'", "ML2", "MU", "MU'", "MU2", "MD", "MD'", "MD2"]


def solved_cube(n):
    from bigcube import cube_from_solved
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


def centers_solved(cube):
    n = cube.size
    for fi, fname in enumerate(FACE_NAMES):
        color = cube.get_facelet(fi, 1, 1)
        for r in range(1, n - 1):
            for c in range(1, n - 1):
                if cube.get_facelet(fi, r, c) != color:
                    return False
    return True


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    t0 = time.time()
    lib = CenterLibrary(n)
    lib.build()
    print(f"原语库构建完成: n={n}, 用时 {time.time()-t0:.1f}s, 条目 {sum(len(v) for v in lib._by_sorted.values())}")

    for trial in range(trials):
        scramble = random_scramble(n, seed=seed + trial)
        cube = solved_cube(n)
        cube.apply_moves(scramble)

        work = solved_cube(n)
        work.apply_moves(scramble)
        t1 = time.time()
        moves, err = solve_centers(work, lib)
        dt = time.time() - t1

        if err:
            print(f"Trial {trial}: 失败: {err} (用时 {dt:.1f}s)")
            continue

        ok = centers_solved(work)
        status = "✓" if ok else "✗"
        print(f"Trial {trial}: 打乱 {len(scramble)} 步, 求解 {len(moves)} 步, 用时 {dt:.1f}s {status}")
        if not ok:
            print("  中心未解!")


if __name__ == "__main__":
    main()
