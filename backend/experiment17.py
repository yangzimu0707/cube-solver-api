# 实验17：5x5 各阶段"最后槽最坏情况"覆盖（q ∈ 未解面\{X}，含 staging）
import sys, itertools
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from centers import CenterLibrary, FACE_NAMES

n = 5
lib = CenterLibrary(n)
lib.build()

slots = [f"{f}{r}{c}" for f in FACE_NAMES for r in (1, 2, 3) for c in (1, 2, 3)]


def find_direct(s, p, q_allow_names):
    for key, entries in lib._by_sorted.items():
        if s not in key or p not in key:
            continue
        for cyc, moves in entries:
            q = [x for x in cyc if x not in (s, p)][0]
            if q[0] not in q_allow_names:
                continue
            if (cyc[0] == p and cyc[1] == s) or \
               (cyc[1] == p and cyc[2] == s) or \
               (cyc[2] == p and cyc[0] == s):
                return True
    return False


def find_staging(s, p, q_allow_names, n):
    free_slots = [q for q in slots if q != s and q[0] in q_allow_names]
    for r in free_slots:
        if not find_direct(r, p, q_allow_names):
            continue
        if find_direct(s, r, q_allow_names):
            return True
    return False


def stage_coverage(X_name, S_names):
    unsolved = [f for f in FACE_NAMES if f not in S_names]
    q_allow = [f for f in unsolved if f != X_name]
    missing = []
    for s in [x for x in slots if x[0] == X_name]:
        for p in slots:
            if p == s or p[0] == X_name or p[0] in S_names:
                continue
            if not find_direct(s, p, q_allow) and not find_staging(s, p, q_allow, n):
                missing.append((s, p))
    return missing


# 打印每个关键阶段的缺失规模
stages = [
    ("U", set()),
    ("F", set()),
    ("U", {"F"}),
    ("D", {"U", "F"}),
    ("F", {"U"}),
    ("F", {"U", "D"}),
    ("L", {"U", "F", "D"}),
    ("B", {"U", "F", "D", "L"}),
    ("R", {"U", "F", "D", "L", "B"}),
]
for X, S in stages:
    miss = stage_coverage(X, S)
    total = sum(1 for s in slots if s[0] == X for p in slots
                if p != s and p[0] != X and p[0] not in S)
    print(f"  目标 {X}, 已解 {sorted(S)}: 覆盖 {total-len(miss)}/{total}, 缺 {len(miss)}")
    if miss:
        print(f"      示例: {miss[:5]}")
