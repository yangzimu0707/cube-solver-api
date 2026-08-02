# 实验13：联合求解最后几面对时的覆盖率（q 可来自联合面任意槽，含 staging）
import sys
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


def check(faces_names, label):
    pair_slots = [s for s in slots if s[0] in faces_names]
    missing = []
    for s in pair_slots:
        for p in pair_slots:
            if p == s:
                continue
            if not find_direct(s, p, faces_names) and not find_staging(s, p, faces_names, n):
                missing.append((s, p))
    print(f"{label}: {len(pair_slots)*(len(pair_slots)-1)} 对, 含staging缺失 {len(missing)}")
    if missing:
        print(f"  缺失示例: {missing[:8]}")
    return missing


# 联合 (B,R)
check(["B", "R"], "(B,R) 联合")
# 联合 (L,B,R)
check(["L", "B", "R"], "(L,B,R) 联合")
# 联合 (F,B,R) / (F,L,R)
check(["F", "B", "R"], "(F,B,R) 联合")
