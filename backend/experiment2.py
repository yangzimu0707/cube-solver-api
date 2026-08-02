# 实验2：带编号贴纸，精确观察算法置换
import sys
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube, cube_from_solved

def labeled_cube(n):
    """每张贴纸用唯一编号（面字母+行列），直接构造 BigCube 绕过长度校验"""
    cube = BigCube.__new__(BigCube)
    cube.size = n
    names = "UFRDBL"  # 输入顺序
    segs = []
    for f in names:
        for r in range(n):
            for c in range(n):
                segs.append(f"{f}{r}{c}")
    # 输入顺序 U,F,R,D,B,L -> 内部顺序 up,down,front,back,left,right
    input_to_internal = {"U": 0, "F": 2, "R": 5, "D": 1, "B": 3, "L": 4}
    facelets = [None] * (6 * n * n)
    for i, f in enumerate(names):
        seg = segs[i * n * n:(i + 1) * n * n]
        internal = input_to_internal[f]
        facelets[internal * n * n:(internal + 1) * n * n] = seg
    cube.facelets = facelets
    return cube

def trace_alg(n, moves, label):
    cube = labeled_cube(n)
    cube.apply_moves(moves.split())
    pos = cube.center_positions()
    print(f"=== {label}: {moves} ===")
    # 打印中心贴纸的来源->去向
    mapping = {}
    for face in range(6):
        for (r, c) in pos[face]:
            val = cube.get_facelet(face, r, c)
            mapping.setdefault(val, []).append((face, r, c))
    for k in sorted(mapping):
        if len(mapping[k]) > 1 or (k[0] != "U" or mapping[k][0][0] != 0):
            # 只打印移动了的（即来源编号 != 目标位置编号）
            for (face, r, c) in mapping[k]:
                src = k
                dst = f"{['U','D','F','B','L','R'][face]}{r}{c}"
                if src != dst:
                    print(f"  {src} -> {dst}")
    print()

# 4x4 中心插入算法
print("######## 4x4 CENTERS ########")
for alg in ["TR U TR'", "TR U2 TR'", "TR U' TR'", "MR U MR'", "MR U' MR'",
            "ML U ML'", "ML U2 ML'", "MU R MU'", "MD R MD'",
            "TR U2 TR' U' TR U TR'", "MR U MR' U' MR U MR'"]:
    trace_alg(4, alg, "4x4-center")

print("######## 4x4 EDGES ########")
for alg in ["TU L' U' L TU'", "TU' R U R' TU", "TD R F' U R' F TD'"]:
    trace_alg(4, alg, "4x4-edge")
