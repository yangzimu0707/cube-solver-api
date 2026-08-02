# 端到端验证 solver444/solver555：打乱 -> serialize -> solve -> 应用 -> is_solved
import sys, random, time
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube, cube_from_solved
from solver444 import solve_444
from solver555 import solve_555

ALL = ["U", "U'", "U2", "D", "D'", "D2", "F", "F'", "F2", "B", "B'", "B2",
       "L", "L'", "L2", "R", "R'", "R2",
       "TR", "TR'", "TR2", "TL", "TL'", "TL2", "TU", "TU'", "TU2", "TD", "TD'", "TD2",
       "MR", "MR'", "MR2", "ML", "ML'", "ML2", "MU", "MU'", "MU2", "MD", "MD'", "MD2"]


def scramble(n, seed, length):
    rng = random.Random(seed)
    out = []
    prev = None
    for _ in range(length):
        m = rng.choice(ALL)
        base = m.rstrip("'2")
        if prev and prev == base:
            continue
        prev = base
        out.append(m)
    return out


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 42
    length = 40 if n == 4 else 60
    fn = solve_444 if n == 4 else solve_555

    for t in range(trials):
        sc = scramble(n, seed + t, length)
        c = BigCube(n, cube_from_solved(n))
        c.apply_moves(sc)
        state = c.serialize()
        t0 = time.time()
        sol = fn(state)
        dt = time.time() - t0
        c2 = BigCube(n, state)
        c2.apply_moves(sol)
        mark = "OK" if c2.is_solved() else "FAIL"
        print(f"{n}x{n} trial{t}: scramble {len(sc)} moves, solution {len(sol)} moves, "
              f"time {dt:.1f}s -> {mark}")


if __name__ == "__main__":
    main()
