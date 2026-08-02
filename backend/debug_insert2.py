# 调试：复现 test_centers 4 1 1 失败点 (F21, L12)，检查该状态下真实可用插入
import sys
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube, FACE_NAMES, cube_from_solved
from centers import CenterLibrary, solve_centers, _find_unfilled_slot, _find_piece, TARGET_COLOR, FACE_NAMES as FN
from test_centers import random_scramble

n = 4
lib = CenterLibrary(n)
lib.build()

scramble = random_scramble(n, seed=1)
cube = BigCube(n, cube_from_solved(n))
cube.apply_moves(scramble)

# 复现贪心：U, D 全解，F 填到 F11, F12
solved_faces = set()
from centers import SOLVE_ORDER, _find_insertion

def dump_face(cube, face_idx):
    fname = FACE_NAMES[face_idx]
    return [[cube.get_facelet(face_idx, r, c) for c in range(1, n-1)] for r in range(1, n-1)]

for tf in SOLVE_ORDER:
    color = TARGET_COLOR[tf]
    print(f"===== 开始解面 {FACE_NAMES[tf]} (solved={[FACE_NAMES[x] for x in solved_faces]}) =====")
    for _ in range(200):
        s = _find_unfilled_slot(cube, tf, color, n)
        if s is None:
            break
        p = _find_piece(cube, color, tf, solved_faces, n)
        print(f"  槽 {s} <- 块 {p}")
        if p is None:
            print("  !! 找不到块")
            break
        seq = _find_insertion(cube, lib, s, p, tf, solved_faces, n)
        if seq is None:
            print(f"  !! 无法插入 {s} 来自 {p}")
            # 打印此时各面中心
            for fi in range(6):
                print(f"   {FACE_NAMES[fi]}面中心: {dump_face(cube, fi)}")
            # 检查所有可用直接 3-cycle
            print("  == 尝试所有可能 p（目标色块）==")
            for fname in FACE_NAMES:
                fi = {"U":0,"D":1,"F":2,"B":3,"L":4,"R":5}[fname]
                if fi == tf or fi in solved_faces:
                    continue
                for r in range(1, n-1):
                    for c in range(1, n-1):
                        if cube.get_facelet(fi, r, c) == color:
                            pp = f"{fname}{r}{c}"
                            seq2 = _find_insertion(cube, lib, s, pp, tf, solved_faces, n)
                            print(f"    p={pp}: {'成功 ' + str(len(seq2)) + '步' if seq2 else '失败'}")
            sys.exit(0)
        cube.apply_moves(seq)
        print(f"    应用 {len(seq)} 步")
    solved_faces.add(tf)
print("完成")
