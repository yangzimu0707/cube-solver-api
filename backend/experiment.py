# 实验脚本：实证标准算法在 bigcube 引擎上的效果
import sys
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube, cube_from_solved, UP, DOWN, FRONT, BACK, LEFT, RIGHT

def show_center_changes(cube, moves, label):
    """在已还原魔方上应用 moves，打印中心块贴纸位置变化"""
    n = cube.size
    before = {}
    pos = cube.center_positions()
    for face in range(6):
        for (r, c) in pos[face]:
            before[(face, r, c)] = cube.get_facelet(face, r, c)
    cube.apply_moves(moves.split())
    print(f"=== {label}: {moves} ===")
    changed = []
    for (face, r, c), v in before.items():
        cur = cube.get_facelet(face, r, c)
        if cur != v:
            changed.append((face, r, c, v, cur))
    for face, r, c, v, cur in changed:
        print(f"  {['U','D','F','B','L','R'][face]}({r},{c}): {v} -> {cur}")
    if not changed:
        print("  (中心块无变化)")

# 4x4 中心算法候选
for alg in ["TR U TR'", "TR U2 TR'", "TD' TR' TD", "TR U TR' U'", "MR U MR'", "MR U' MR'", "ML U ML'"]:
    cube = BigCube(4, cube_from_solved(4))
    show_center_changes(cube, alg, "4x4")

print()
# 4x4 棱块配对算法效果（观察 U 层棱）
def show_edge_changes(cube, moves, label):
    n = cube.size
    before = {}
    # U 面边缘贴纸
    for face in range(6):
        for idx in range(n):
            # 每面四条边: 上(row0), 下(row n-1), 左(col0), 右(col n-1)
            edges = [(0, idx), (n-1, idx), (idx, 0), (idx, n-1)]
            for (r, c) in edges:
                before[(face, r, c)] = cube.get_facelet(face, r, c)
    cube.apply_moves(moves.split())
    print(f"=== {label}: {moves} ===")
    cnt = 0
    for (face, r, c), v in before.items():
        cur = cube.get_facelet(face, r, c)
        if cur != v:
            cnt += 1
            if cnt <= 24:
                print(f"  {['U','D','F','B','L','R'][face]}({r},{c}): {v} -> {cur}")
    print(f"  (共 {cnt} 处变化)")

for alg in ["TU L' U' L TU'", "TU' R U R' TU", "TD R F' U R' F TD'", "R U' B' R2"]:
    cube = BigCube(4, cube_from_solved(4))
    show_edge_changes(cube, alg, "4x4-edge")
