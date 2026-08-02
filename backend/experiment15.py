# 实验15：检查所有 15 个面对组合的联合求解覆盖（q ∈ 面对任意槽，含 staging）
import sys, itertools
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from centers import CenterLibrary, FACE_NAMES

n = 4
lib = CenterLibrary(n)
lib.build()

slots = [f"{f}{r}{c}" for f in FACE_NAMES for r in (1, 2) for c in (1, 2)]


def find_direct(s, p, allow_names):
    for key, entries in lib._by_sorted.items():
        if s not in key or p not in key:
            continue
        for cyc, moves in entries:
            q = [x for x in cyc if x not in (s, p)][0]
            if q[0] not in allow_names:
                continue
            if (cyc[0] == p and cyc[1] == s) or \
               (cyc[1] == p and cyc[2] == s) or \
               (cyc[2] == p and cyc[0] == s):
                return True
    return False


def find_staging(s, p, allow_names, n):
    free_slots = [q for q in slots if q != s and q[0] in allow_names]
    for r in free_slots:
        if not find_direct(r, p, allow_names):
            continue
        if find_direct(s, r, allow_names):
            return True
    return False


print("所有面对组合的联合覆盖（q ∈ 两面对任意槽）")
for a, b in itertools.combinations(FACE_NAMES, 2):
    pair_slots = [s for s in slots if s[0] in (a, b)]
    missing = []
    for s in pair_slots:
        for p in pair_slots:
            if p == s:
                continue
            if not find_direct(s, p, [a, b]) and not find_staging(s, p, [a, b], n):
                missing.append((s, p))
    status = "✓全覆盖" if not missing else f"缺{len(missing)}"
    print(f"  ({a},{b}): {status}")
    if missing:
        print(f"      示例: {missing[:6]}")
