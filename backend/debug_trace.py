# 调试：追踪 solve_centers 卡死位置
import sys
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube, FACE_NAMES, cube_from_solved
from centers import CenterLibrary, solve_centers, TARGET_COLOR, SOLVE_ORDER, _find_unfilled_slot, _insert_any_candidate, _make_free_rule
from test_centers import random_scramble

n = 4
lib = CenterLibrary(n)
lib.build()
scramble = random_scramble(n, seed=1)
cube = BigCube(n, cube_from_solved(n))
cube.apply_moves(scramble)
print("打乱:", " ".join(scramble))

solved_faces = set()
solved_names = set()
for i, tf in enumerate(SOLVE_ORDER[:4]):
    tf_name = FACE_NAMES[tf]
    color = TARGET_COLOR[tf]
    if i < 4:
        free_rule = _make_free_rule(solved_names, tf_name, cube)
    else:
        free_rule = _make_free_rule(solved_names, None, cube)
    print(f"===== 阶段1 面 {tf_name} (solved={sorted(solved_names)}) =====")
    for it in range(30):
        s = _find_unfilled_slot(cube, tf, color, n)
        if s is None:
            print(f"  完成，用时 {it} 次迭代")
            break
        seq = _insert_any_candidate(cube, lib, s, tf, color, solved_faces, None, free_rule, n)
        if seq is None:
            print(f"  !! 无法插入 槽 {s}")
            for fi, fname in enumerate(FACE_NAMES):
                print(f"   {fname}面: {[[cube.get_facelet(fi,r,c) for c in range(1,n-1)] for r in range(1,n-1)]}")
            sys.exit(0)
        cube.apply_moves(seq)
        if it % 5 == 0:
            print(f"  迭代 {it}: 填 {s}, 用 {len(seq)} 步")
    else:
        print(f"  !! 面 {tf_name} 超过 30 次迭代仍未完成（循环）")
        for fi, fname in enumerate(FACE_NAMES):
            print(f"   {fname}面: {[[cube.get_facelet(fi,r,c) for c in range(1,n-1)] for r in range(1,n-1)]}")
        sys.exit(0)
    solved_faces.add(tf)
    solved_names.add(tf_name)

print("全部完成（阶段1）")

# 阶段2：联合 B, L
joint = SOLVE_ORDER[4:]
joint_idx = set(joint)
free_rule = _make_free_rule(solved_names, None, cube)
print("===== 阶段2 联合 (B, L) =====")
for it in range(60):
    tf = None
    s = None
    for f in joint:
        s = _find_unfilled_slot(cube, f, TARGET_COLOR[f], n)
        if s is not None:
            tf = f
            break
    if s is None:
        print(f"  完成，用时 {it} 次迭代")
        break
    color = TARGET_COLOR[tf]
    seq = _insert_any_candidate(cube, lib, s, tf, color, solved_faces, joint_idx, free_rule, n)
    if seq is None:
        print(f"  !! 无法插入 槽 {s}（面 {FACE_NAMES[tf]}）")
        break
    cube.apply_moves(seq)
    if it % 10 == 0:
        b = [[cube.get_facelet(3,r,c) for c in range(1,n-1)] for r in range(1,n-1)]
        l = [[cube.get_facelet(4,r,c) for c in range(1,n-1)] for r in range(1,n-1)]
        print(f"  迭代 {it}: 填 {s}, 用 {len(seq)} 步 | B面={b} L面={l}")
else:
    print(f"  !! 联合阶段超过 60 次迭代仍未完成（循环）")
    for fi, fname in enumerate(FACE_NAMES):
        print(f"   {fname}面: {[[cube.get_facelet(fi,r,c) for c in range(1,n-1)] for r in range(1,n-1)]}")
    sys.exit(0)
