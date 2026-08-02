# 实验12：检查每个阶段 (s,p) 的直接 + staging 两跳覆盖
# staging: p -> r -> s（r 为自由槽）
import sys
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from centers import CenterLibrary, SOLVE_ORDER, TARGET_COLOR, FACE_NAMES

n = 4
lib = CenterLibrary(n)
lib.build()

FI = {f: i for i, f in enumerate(FACE_NAMES)}
slots = [f"{f}{r}{c}" for f in FACE_NAMES for r in (1, 2) for c in (1, 2)]


def find_direct(s, p, protected_names):
    for key, entries in lib._by_sorted.items():
        if s not in key or p not in key:
            continue
        for cyc, moves in entries:
            q = [x for x in cyc if x not in (s, p)][0]
            if q[0] in protected_names:
                continue
            if (cyc[0] == p and cyc[1] == s) or \
               (cyc[1] == p and cyc[2] == s) or \
               (cyc[2] == p and cyc[0] == s):
                return True
    return False


def find_staging(s, p, protected_names, n):
    """p -> r -> s"""
    free_slots = [q for q in slots if q != s and q[0] not in protected_names]
    for r in free_slots:
        if not find_direct(r, p, protected_names):
            continue
        if find_direct(s, r, protected_names):
            return True
    return False


for i, target_face in enumerate(SOLVE_ORDER):
    tf_name = FACE_NAMES[target_face]
    protected = [FACE_NAMES[x] for x in SOLVE_ORDER[:i]]
    missing_direct = []
    missing_staging = []
    total = 0
    for s in slots:
        if s[0] != tf_name:
            continue
        for p in slots:
            if p == s or p[0] in protected:
                continue
            total += 1
            if not find_direct(s, p, protected):
                missing_direct.append((s, p))
                if not find_staging(s, p, protected, n):
                    missing_staging.append((s, p))
    print(f"面 {tf_name}: 共 {total}, 直接缺失 {len(missing_direct)}, 含 staging 仍缺失 {len(missing_staging)}")
    if missing_staging:
        print(f"  含 staging 仍缺失: {missing_staging[:8]}")
