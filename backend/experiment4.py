# 实验4：枚举所有 (slice, face) 换位子环，并寻找共享单点的环对的对易子（3-cycle 原语）
import sys, itertools
sys.path.insert(0, r"c:\Users\yzm20\Desktop\新的 App.swiftpm\新的 App.swiftpm\backend")
from bigcube import BigCube

FACE_NAMES = ["U", "D", "F", "B", "L", "R"]


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


def cycle_decomp(moves, n=4):
    """返回对中心块位置的作用，用 dict: 位置 -> 该位置收到来自哪个位置的块"""
    cube = labeled_cube(n)
    cube.apply_moves(moves)
    pos = cube.center_positions()
    mapping = {}  # dst -> src (src 位置上的块现在在 dst)
    for face in range(6):
        for (r, c) in pos[face]:
            src = cube.get_facelet(face, r, c)
            dst = f"{FACE_NAMES[face]}{r}{c}"
            mapping[dst] = src
    return mapping


def to_cycles(mapping):
    """把 dst->src 映射转成 块移动循环（piece 移动方向）: 每个循环列出位置序列
    piece 移动：src -> dst。循环格式 (a b c) 表示 a 位置的块移到 b, b 移到 c, c 移到 a。"""
    # 先从 dst->src 推出 src->dst（块移动）
    move = {}
    for dst, src in mapping.items():
        move[src] = dst
    visited = set()
    cycles = []
    for start in move:
        if start in visited:
            continue
        cur = start
        cyc = []
        while cur not in visited:
            visited.add(cur)
            cyc.append(cur)
            cur = move[cur]
        if len(cyc) > 1:
            cycles.append(cyc)
    return cycles


def invert_cycles(cycles):
    """取循环的逆"""
    return [c[::-1] for c in cycles]


def compose(cycles1, cycles2):
    """返回先应用 cycles1 再应用 cycles2 的合成（作用于位置序列）：
    piece 在 cycles1 移动后再按 cycles2 移动。"""
    move1 = {}
    for c in cycles1:
        for i in range(len(c)):
            move1[c[i]] = c[(i + 1) % len(c)]
    move2 = {}
    for c in cycles2:
        for i in range(len(c)):
            move2[c[i]] = c[(i + 1) % len(c)]
    # 合成：先 move1 再 move2
    move = {}
    for k in set(move1) | set(move2):
        mid = move1.get(k, k)
        move[k] = move2.get(mid, mid)
    visited = set()
    result = []
    for start in move:
        if start in visited:
            continue
        cur = start
        cyc = []
        while cur not in visited:
            visited.add(cur)
            cyc.append(cur)
            cur = move[cur]
        if len(cyc) > 1:
            result.append(cyc)
    return result


if __name__ == "__main__":
    n = 4
    slices = ["MR", "ML", "MU", "MD"]
    faces = ["U", "D", "F", "B", "L", "R"]

    print("#### 所有 (slice, face) 环 ####")
    rings = {}
    for s in slices:
        for f in faces:
            alg = f"{s} {f} {s}'"
            cyc = to_cycles(cycle_decomp(alg.split(), n))
            rings[(s, f)] = cyc
            print(f"{alg:12s} -> {cyc}")

    print()
    print("#### 共享单点的环对对易子 [p,q]=p q p' q' ####")
    items = list(rings.items())
    found = 0
    for (s1, f1), c1 in items:
        for (s2, f2), c2 in items:
            if (s1, f1) >= (s2, f2):
                continue
            # 计算公共元素
            pieces1 = set(itertools.chain.from_iterable(c1))
            pieces2 = set(itertools.chain.from_iterable(c2))
            common = pieces1 & pieces2
            if len(common) != 1:
                continue
            # [p,q] = p q p' q'
            c1_inv = invert_cycles(c1)
            c2_inv = invert_cycles(c2)
            # 按顺序: 先 p, 再 q, 再 p', 再 q'
            step = c1
            step = compose(step, c2)
            step = compose(step, c1_inv)
            step = compose(step, c2_inv)
            comm = [c for c in step if len(c) > 1]
            # 只关注中心块上的循环
            comm_centers = [c for c in comm if len(c) == 3 and all(
                any(p in pieces1 for p in c) or any(p in pieces2 for p in c) for _ in [0])]
            if len(comm) == 1 and len(comm[0]) == 3:
                print(f"[{s1} {f1} {s1}'  ,  {s2} {f2} {s2}'] 共享 {sorted(common)} -> 3-cycle {comm[0]}")
                found += 1
    print(f"\n共找到 {found} 个 3-cycle 原语")
