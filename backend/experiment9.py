# 诊断：用修正后的 CenterLibrary 检查逐面插入覆盖
import sys
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from centers import CenterLibrary, SOLVE_ORDER, TARGET_COLOR, FACE_NAMES

n = 4
lib = CenterLibrary(n)
lib.build()

# 面索引
FI = {f: i for i, f in enumerate(FACE_NAMES)}
slots = [f"{f}{r}{c}" for f in FACE_NAMES for r in (1, 2) for c in (1, 2)]

solved_before = {}
for i, face in enumerate(SOLVE_ORDER):
    solved_before[face] = set(SOLVE_ORDER[:i])

print("求解顺序:", [FACE_NAMES[f] for f in SOLVE_ORDER])

for target_face in SOLVE_ORDER:
    tf_name = FACE_NAMES[target_face]
    protected = solved_before[target_face]
    # 该阶段可用的第三个槽：不在已解面
    missing = []
    total = 0
    for s in slots:
        if s[0] != tf_name:
            continue
        for p in slots:
            if p == s or p[0] in [FACE_NAMES[x] for x in protected]:
                continue
            total += 1
            # 检查是否存在 3-cycle (p s q) 且 q 不在已解面
            found = False
            for key, entries in lib._by_sorted.items():
                if s not in key or p not in key:
                    continue
                for cyc, moves in entries:
                    q = [x for x in cyc if x not in (s, p)][0]
                    if q[0] in [FACE_NAMES[x] for x in protected]:
                        continue
                    if (cyc[0] == p and cyc[1] == s) or (cyc[1] == p and cyc[2] == s) or (cyc[2] == p and cyc[0] == s):
                        found = True
                        break
                if found:
                    break
            if not found:
                missing.append((s, p))
    print(f"面 {tf_name}: 覆盖 {total - len(missing)}/{total}, 缺失 {len(missing)}")
    for m in missing[:10]:
        print("   ", m)
