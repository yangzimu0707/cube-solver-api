# 实验14：检查每个阶段 (X, S) 的"最后槽最坏情况"覆盖
# 严格规则：q 不能来自已解面 S，也不能来自目标面 X 的已填槽
# 最后槽最坏情况：q 只能来自 未解面 \ {X}
# 若某阶段全覆盖（含 staging），则严格贪心在该阶段一定能完成
import sys
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from centers import CenterLibrary, FACE_NAMES

n = 4
lib = CenterLibrary(n)
lib.build()

slots = [f"{f}{r}{c}" for f in FACE_NAMES for r in (1, 2) for c in (1, 2)]


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
    """目标面 X，已解面集合 S。检查 (s,p) 全覆盖（q ∈ 未解\X）。返回缺失列表。"""
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


# 逐个阶段打印
import itertools
print("检查各阶段最后槽最坏情况覆盖（q ∈ 未解面\\{X}）")
for X in FACE_NAMES:
    others = [f for f in FACE_NAMES if f != X]
    for k in range(1, len(others)):
        for S in itertools.combinations(others, k):
            miss = stage_coverage(X, set(S))
            mark = "✓" if not miss else f"缺{len(miss)}"
            print(f"  目标 {X}, 已解 {sorted(S)}: {mark}")
            if miss:
                print(f"      示例: {miss[:4]}")
