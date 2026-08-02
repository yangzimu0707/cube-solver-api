# 查看 5x5 的 base 3-cycle 结构
import sys
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube, FACE_NAMES
from centers import SLICES, FACES, _inv, _cycle_decomp, TARGET_COLOR

n = 5
slot_names = set(f"{f}{r}{c}" for f in FACE_NAMES for r in (1, 2, 3) for c in (1, 2, 3))

slices = SLICES + ["M", "E", "S"]
rings = {}
for s in slices:
    for f in FACES:
        rings[(s, f)] = [s, f, _inv(s)]

found = []
items = list(rings.items())
for (s1, f1), p in items:
    for (s2, f2), q in items:
        if (s1, f1) >= (s2, f2):
            continue
        p_inv = [p[0], _inv(p[1]), p[2]]
        q_inv = [q[0], _inv(q[1]), q[2]]
        comm = p + q + p_inv + q_inv
        cyc = _cycle_decomp(comm, n, slot_names)
        if len(cyc) == 1 and len(cyc[0]) == 3:
            found.append((tuple(cyc[0]), s1, f1, s2, f2, comm))

print(f"base 3-cycle 数: {len(found)}")
for c, s1, f1, s2, f2, comm in sorted(found, key=lambda x: x[0]):
    print(f"  {c}  <= [{s1}{f1}{s1}', {s2}{f2}{s2}']: {' '.join(comm)}")
