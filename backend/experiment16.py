# 诊断 5x5：环结构 + 环对易子 3-cycle 数量 + 共轭覆盖
import sys
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube, FACE_NAMES
from centers import CenterLibrary, SLICES, FACES, _inv, _cycle_decomp

n = 5
slot_names = set(f"{f}{r}{c}" for f in FACE_NAMES for r in (1, 2, 3) for c in (1, 2, 3))

rings = {}
for s in SLICES:
    for f in FACES:
        rings[(s, f)] = [s, f, _inv(s)]

# 环的实际循环（中心槽）
print("===== 5x5 环结构 =====")
for (s, f), alg in rings.items():
    cyc = _cycle_decomp(alg, n, slot_names)
    lens = sorted(len(c) for c in cyc)
    print(f"  {s} {f} {s}': {len(cyc)} 个循环, 长度 {lens}")

# 环对易子
found = {}
items = list(rings.items())
for (s1, f1), p in items:
    for (s2, f2), q in items:
        if (s1, f1) >= (s2, f2):
            continue
        p_inv = [p[0], _inv(p[1]), p[2]]
        q_inv = [q[0], _inv(q[1]), q[2]]
        comm = p + q + p_inv + q_inv
        cyc = _cycle_decomp(comm, n, slot_names)
        key = tuple(sorted(len(c) for c in cyc))
        found.setdefault(key, []).append((s1, f1, s2, f2))
print("\n===== 环对易子循环结构 =====")
for key, count in sorted(found.items()):
    print(f"  循环长度分布 {key}: {len(count)} 对")
