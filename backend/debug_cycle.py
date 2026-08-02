# 调试：验证库中每个 3-cycle 的动作序列确实实现所声明的循环
import sys
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube, FACE_NAMES
from centers import CenterLibrary

n = 4


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


def get_piece_mapping(cube):
    mapping = {}
    for fi, fname in enumerate(FACE_NAMES):
        for (r, c) in cube.center_positions()[fi]:
            src = cube.get_facelet(fi, r, c)
            mapping[f"{fname}{r}{c}"] = src
    return mapping


lib = CenterLibrary(n)
lib.build()

bad = 0
tested = 0
for key, entries in lib._by_sorted.items():
    for cyc, moves in entries:
        cube = labeled_cube(n)
        cube.apply_moves(moves)
        mapping = get_piece_mapping(cube)
        ok = True
        a, b, c = cyc
        if mapping[b] != a or mapping[c] != b or mapping[a] != c:
            ok = False
        tested += 1
        if not ok:
            bad += 1
            if bad <= 5:
                print(f"错误: 循环 {cyc} 动作 {moves}")
                print(f"  实际: {mapping}")

print(f"测试 {tested} 个，错误 {bad}，库条目 {sum(len(v) for v in lib._by_sorted.values())}")
