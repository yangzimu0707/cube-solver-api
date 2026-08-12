# 完整端到端验证（4x4/5x5 降阶法 + parity 处理）：
# 打乱 -> solve_centers -> solve_edges_pair -> 提取3x3 -> kociemba
#   Flip error   -> 应用 OLL parity（保持中心+边配对）
#   Parity error -> 应用 PLL parity（r2 U2 r2 Uw2 r2 Uw2，保持中心；不重配对）
# 应用解法 -> is_solved
import sys, os, random, time, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".kociemba_src", "kociemba-1.2.1"))
import warnings
warnings.filterwarnings("ignore")
import kociemba

from bigcube import BigCube, cube_from_solved, FACE_NAMES
from centers import CenterLibrary, solve_centers
from edges_reduce import (EdgeReduceLibrary, solve_edges_pair, extract_3x3,
                          edge_lines)

# r2 B2 U2 l U2 r' U2 r U2 F2 r F2 l' B2 r2  （保持中心 + 保持边配对，只翻转一个中棱）
OLL_PARITY = ["MR2", "B2", "U2", "ML", "U2", "MR'", "U2", "MR", "U2",
              "F2", "MR", "F2", "ML'", "B2", "MR2"]
# r2 U2 r2 Uw2 r2 Uw2  （保持中心，交换两个中棱 + 两个角；破坏边配对需重新配对）
PLL_PARITY = ["MR2", "U2", "MR2", "TU2", "MR2", "TU2"]

ALL_MOVES = ["U", "U'", "U2", "D", "D'", "D2", "F", "F'", "F2", "B", "B'", "B2",
             "L", "L'", "L2", "R", "R'", "R2", "TR", "TR'", "TR2", "TL", "TL'", "TL2",
             "TU", "TU'", "TU2", "TD", "TD'", "TD2", "MR", "MR'", "MR2", "ML", "ML'", "ML2",
             "MU", "MU'", "MU2", "MD", "MD'", "MD2"]


def random_scramble(n, seed, length):
    rng = random.Random(seed)
    moves, prev = [], None
    for _ in range(length):
        m = rng.choice(ALL_MOVES)
        base = m.rstrip("'2")
        if prev and prev == base:
            continue
        prev = base
        moves.append(m)
    return moves


def edges_solved(cube):
    n = cube.size
    facet_info, sid_of = [], {}
    for f in range(6):
        for r in range(n):
            for c in range(n):
                if (r == 0 or r == n - 1) != (c == 0 or c == n - 1):
                    sid_of[(f, r, c)] = len(facet_info)
                    facet_info.append((f, r, c))
    line_of = {}
    for line in edge_lines(n):
        colors = {FACE_NAMES[f] for (f, r, c) in line}
        for pos in line:
            line_of[sid_of[pos]] = colors
    return all(cube.get_facelet(*facet_info[x]) in line_of[x]
               for x in range(len(facet_info)))


def parity_fix_and_solve(cube, libe, n):
    """提取 3x3 -> kociemba；按错误类型应用 OLL/PLL parity。返回 (moves, used_parity, error)。
    OLL（Flip error）：翻转一个中棱，保持中心+边配对。
    PLL（Parity error）：交换两个中棱+两个角，保持中心，不破坏边配对结构。
    两者可能同时需要（先 OLL 后 PLL 或反之）。"""
    applied_oll = False
    applied_pll = False
    for attempt in range(6):
        s3 = extract_3x3(cube)
        try:
            sol = kociemba.solve(s3)
            return sol.split(), applied_oll or applied_pll, None
        except Exception as e:
            msg = str(e)
            is_flip = "Flip" in msg or "flipped" in msg
            is_parity = "Parity" in msg
            if n != 4:
                return None, False, f"n={n} 但 kociemba 拒绝: {e}"
            if is_flip and not applied_oll:
                cube.apply_moves(OLL_PARITY)
                applied_oll = True
                continue
            if is_parity and not applied_pll:
                cube.apply_moves(PLL_PARITY)
                applied_pll = True
                continue
            # 已应用过对应修复仍失败
            return None, True, f"parity 修复后仍被拒: {e}"
    return None, True, "parity 修复超过尝试上限"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 8

    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "cache", f"edger{n}.pkl"), "rb") as fh:
        libe = pickle.load(fh)
    libc = CenterLibrary(n)
    libc.build()

    n_ok, n_oll, n_pll = 0, 0, 0
    for t in range(trials):
        scr = random_scramble(n, seed=500 + t, length=40 if n == 4 else 60)
        cube = BigCube(n, cube_from_solved(n))
        cube.apply_moves(scr)

        t0 = time.time()
        cmoves, cerr = solve_centers(cube, libc)
        if cerr:
            print(f"Trial {t}: 中心失败 {cerr}")
            continue
        emoves, eerr = solve_edges_pair(cube, libe)
        if eerr:
            print(f"Trial {t}: 边配对失败 {eerr}")
            continue
        if not edges_solved(cube):
            print(f"Trial {t}: 边未全对")
            continue

        kmoves, used_parity, perr = parity_fix_and_solve(cube, libe, n)
        if perr:
            print(f"Trial {t}: {perr}")
            continue
        cube.apply_moves(kmoves)

        ok = cube.is_solved()
        total = len(cmoves) + len(emoves) + len(kmoves)
        which = ("OLL" if used_parity and "OLL" in "" else "")
        status = "✓还原" if ok else "✗未还原"
        print(f"Trial {t}: 中心{len(cmoves)} 边{len(emoves)} kociemba{len(kmoves)} "
              f"parity={'是' if used_parity else '否'} 合计{total}步 "
              f"用时{time.time()-t0:.1f}s {status}")
        if ok:
            n_ok += 1
        else:
            bad = [(FACE_NAMES[f], r, c, cube.get_facelet(f, r, c))
                   for f in range(6) for r in range(n) for c in range(n)
                   if cube.get_facelet(f, r, c) != FACE_NAMES[f]]
            print("   错误贴纸:", bad[:12])

    print(f"\n汇总: {n_ok}/{trials}")


if __name__ == "__main__":
    main()
