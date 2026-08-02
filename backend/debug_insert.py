# 调试：单独测试 (U11, D12) 插入
import sys, random
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube, FACE_NAMES
from centers import CenterLibrary, solve_centers, _find_insertion, _find_unfilled_slot, _find_piece, TARGET_COLOR

n = 4
lib = CenterLibrary(n)
lib.build()

from bigcube import cube_from_solved
ALL_MOVES = ["U", "U'", "U2", "D", "D'", "D2", "F", "F'", "F2", "B", "B'", "B2",
             "L", "L'", "L2", "R", "R'", "R2",
             "TR", "TR'", "TR2", "TL", "TL'", "TL2", "TU", "TU'", "TU2", "TD", "TD'", "TD2",
             "MR", "MR'", "MR2", "ML", "ML'", "ML2", "MU", "MU'", "MU2", "MD", "MD'", "MD2"]

# 找到能复现失败的打乱
for seed in range(50):
    rng = random.Random(seed)
    moves = []
    prev = None
    for _ in range(40):
        m = rng.choice(ALL_MOVES)
        b = m.rstrip("'2")
        if b == prev:
            continue
        prev = b
        moves.append(m)
    cube = BigCube(4, cube_from_solved(4))
    cube.apply_moves(moves)
    s = _find_unfilled_slot(cube, 0, 'U', 4)
    if s == "U11":
        p = _find_piece(cube, 'U', 0, set(), 4)
        if p == "D12":
            print(f"seed={seed} 复现: s={s}, p={p}")
            print("打乱:", moves)
            # 详细调试
            from centers import FACE_NAMES as FN
            qn2i = {name: i for i, name in enumerate(FN)}
            def free_rule(q):
                if q is None:
                    return False
                qi = qn2i[q[0]]
                if qi in set():
                    return False
                if qi == 0:
                    if cube.get_facelet(0, int(q[1]), int(q[2])) == TARGET_COLOR[0]:
                        return False
                return True
            hit = lib.find_cycle(("U11", "D12"), None, free_rule)
            print("直接:", hit[1] if hit else None)
            free_slots = []
            for fname in FN:
                fi = qn2i[fname]
                if fi in set():
                    continue
                for r in (1, 2):
                    for c in (1, 2):
                        q = f"{fname}{r}{c}"
                        if q != "U11" and free_rule(q):
                            free_slots.append(q)
            print("free_slots:", free_slots)
            for r_slot in free_slots:
                h1 = lib.find_cycle((r_slot, "D12"), None, free_rule)
                if h1:
                    h2 = lib.find_cycle(("U11", r_slot), None, free_rule)
                    if h2:
                        print(f"staging via {r_slot}: hop1={h1[0]} seq={h1[1]}, hop2={h2[0]} seq={h2[1]}")
                        break
            else:
                # 打印几个失败的 hop1/hop2 示例
                for r_slot in free_slots[:8]:
                    h1 = lib.find_cycle((r_slot, "D12"), None, free_rule)
                    print(f"  {r_slot}: hop1={h1[0] if h1 else None}")
            break
