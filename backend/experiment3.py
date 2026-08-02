# 实验3：实证所有换位子环的位置（4x4 中心）
import sys
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube

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

def trace_alg(n, moves, label):
    cube = labeled_cube(n)
    cube.apply_moves(moves.split())
    pos = cube.center_positions()
    changes = []
    for face in range(6):
        for (r, c) in pos[face]:
            val = cube.get_facelet(face, r, c)
            src = val
            dst = f"{['U','D','F','B','L','R'][face]}{r}{c}"
            if src != dst:
                changes.append((src, dst))
    print(f"=== {label}: {moves} ===")
    for src, dst in sorted(changes):
        print(f"  {src} -> {dst}")
    print()

print("#### 4x4 换位子环 ####")
# MR/ML + U/D
for alg in ["MR U MR'", "MR U' MR'", "MR U2 MR'",
            "MR D MR'", "MR D' MR'", "MR D2 MR'",
            "ML U ML'", "ML U' ML'",
            "ML D ML'", "ML D' ML'",
            "MU R MU'", "MU R' MU'", "MU R2 MU'",
            "MU L MU'", "MU L' MU'",
            "MD R MD'", "MD R' MD'",
            "MD L MD'", "MD L' MD'"]:
    trace_alg(4, alg, "4x4-ring")
