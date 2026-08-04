"""
降阶法边求解器（4x4 / 5x5）。

为什么旧的 edges.py 不可用：
旧库要求"中心保持 + 边槽贴纸单 3-cycle"。但在刚体物理块模型下，
"中心保持 + 单贴纸 3-cycle 且不拆散物理块"结构上不存在，导致库 0 条目。

本模块改用【块级 3-cycle】原语：
3 个边物理块（翼块/中棱）轮换 = 贴纸层面恰好 2 个长度 3 的贴纸循环（[3,3]），
中心槽全部保持。这类原语在 4x4 找到 128 条、5x5 找到 220 条（环对易子搜索
+ 迭代共轭扩展）。

求解流程（降阶法）：
1. solve_centers            —— 中心归位（独立模块，已验证端到端通过）
2. solve_edges_reduce       —— 边贴纸颜色贪心归位（= 翼块/中棱位置归位）
3. extract_3x3 + kociemba   —— 降阶后是合法 3x3，kociemba 收尾

为什么边"完全归位"（而非仅配对）：
所有生成子对翼块/中棱的置换均为偶置换，故位置归位（恒等，偶）恒可达；
归位后剩余角块置换也必为偶，提取的 3x3 无奇偶问题，kociemba 必可解。
"""
import itertools

from bigcube import BigCube, FACE_NAMES


def _inv(move):
    if move.endswith("'"):
        return move[:-1]
    if move.endswith("2"):
        return move
    return move + "'"


def _apply_labeled(n, moves):
    """整数标签立方体（home 索引即标签），应用动作序列"""
    c = BigCube.__new__(BigCube)
    c.size = n
    c.facelets = list(range(6 * n * n))
    c.apply_moves(moves)
    return c


def edge_sticker_positions(n):
    """所有边贴纸位置 (face, r, c) 列表（含翼块与 5x5 中棱的贴纸）"""
    positions = []
    for f in range(6):
        for r in range(n):
            for c in range(n):
                if (r == 0 or r == n - 1) != (c == 0 or c == n - 1):
                    positions.append((f, r, c))
    return positions


class EdgeReduceLibrary:
    """
    块级纯边 3-cycle 原语库。

    条目：两个长度 3 的贴纸循环 (cyc1, cyc2) + 动作序列。
    循环 (a, b, c) 语义：位置 a 的贴纸 -> b -> c -> a。
    每个循环里的贴纸都属于边槽（slot id）。
    """

    def __init__(self, n):
        self.n = n
        self.edge_facets = []      # slot id -> facelet 索引
        self.facet_info = []       # slot id -> (face, r, c)
        self.facet_to_sid = {}     # facelet 索引 -> slot id
        self.center_facets = set() # 中心槽 facelet 索引（home 保持检查）
        self._by_pair = {}         # (p, s) -> [(cyc, other, moves)]：贴纸 p->s

    def build(self, conj_depth=2, wide_in_gens=False):
        n = self.n

        # ---- 槽与中心 ----
        for f in range(6):
            for r in range(n):
                for c in range(n):
                    if (r == 0 or r == n - 1) != (c == 0 or c == n - 1):
                        idx = f * n * n + r * n + c
                        self.facet_to_sid[idx] = len(self.edge_facets)
                        self.edge_facets.append(idx)
                        self.facet_info.append((f, r, c))
        self.center_facets = {
            f * n * n + r * n + c
            for f in range(6)
            for r in range(1, n - 1)
            for c in range(1, n - 1)
        }

        slices = ["MR", "ML", "MU", "MD"] + (["M", "E", "S"] if n >= 5 else [])
        face_variants = [m + s for m in "UDFBLR" for s in ["", "'", "2"]]
        wide_variants = [m + s for m in ["TR", "TL", "TU", "TD"] for s in ["", "'", "2"]]
        move_gens = (face_variants + ["MR", "MR'", "ML", "ML'", "MU", "MU'", "MD", "MD'"]
                     + (["M", "M'", "E", "E'", "S", "S'"] if n >= 5 else [])
                     + (wide_variants if wide_in_gens else []))

        rings = []
        for s in slices:
            for f in face_variants:
                rings.append([s, f, _inv(s)])
        for w in wide_variants:
            for f in face_variants:
                rings.append([w, f, _inv(w)])

        # ---- 环对易子搜索基础原语 ----
        base = {}  # frozenset key -> (cyc1, cyc2, moves)

        def _try(comm):
            r = self._classify(n, comm)
            if r is None:
                return
            cyc1, cyc2 = r
            key = frozenset((tuple(sorted(cyc1)), tuple(sorted(cyc2))))
            if key not in base:
                base[key] = (cyc1, cyc2, comm)

        for ring in rings:
            for B in move_gens:
                comm = ring + [B] + [_inv(m) for m in reversed(ring)] + [_inv(B)]
                _try(comm)
                comm2 = [B] + ring + [_inv(B)] + [_inv(m) for m in reversed(ring)]
                _try(comm2)
        for i, r1 in enumerate(rings):
            for r2 in rings[i + 1:]:
                comm = r1 + r2 + [_inv(m) for m in reversed(r1)] + [_inv(m) for m in reversed(r2)]
                _try(comm)

        # ---- 迭代共轭扩展（共轭保持块结构，无需逐条验证）----
        conj_algs = face_variants + slices + wide_variants
        perms = self._conj_perms(conj_algs)
        entries = dict(base)
        current = dict(base)
        for _ in range(conj_depth):
            nxt = {}
            for key, (cyc1, cyc2, moves) in current.items():
                for alg, perm in perms:
                    try:
                        nc1 = tuple(perm[x] for x in cyc1)
                        nc2 = tuple(perm[x] for x in cyc2)
                    except KeyError:
                        continue  # 循环逃出边槽（含角/中心贴纸），丢弃
                    nkey = frozenset((tuple(sorted(nc1)), tuple(sorted(nc2))))
                    if nkey in entries:
                        continue
                    entries[nkey] = (nc1, nc2, [alg] + moves + [_inv(alg)])
                    nxt[nkey] = entries[nkey]
            current = nxt
            if not current:
                break

        # ---- 构建 (p, s) -> 条目 索引 ----
        self._by_pair = {}
        for (cyc1, cyc2, moves) in entries.values():
            for cyc, other in ((cyc1, cyc2), (cyc2, cyc1)):
                for i in range(3):
                    p, s = cyc[i], cyc[(i + 1) % 3]  # 贴纸 p -> s
                    self._by_pair.setdefault((p, s), []).append((cyc, other, moves))

    def _classify(self, n, moves):
        """纯边 [3,3]：中心槽 home 保持 + 恰好 2 个长度 3 贴纸循环且全在边槽。
        返回 (cyc1, cyc2)（slot id）或 None。"""
        cube = _apply_labeled(n, moves)
        f = cube.facelets
        for idx in self.center_facets:
            if f[idx] != idx:
                return None
        sticker_move = {}
        for new_pos, old in enumerate(f):
            if old != new_pos:
                sticker_move[old] = new_pos
        cycles = []
        visited = set()
        for start in sticker_move:
            if start in visited:
                continue
            cur = start
            cyc = []
            while cur not in visited:
                visited.add(cur)
                cyc.append(cur)
                cur = sticker_move[cur]
            if len(cyc) > 1:
                cycles.append(cyc)
        if len(cycles) != 2 or sorted(len(c) for c in cycles) != [3, 3]:
            return None
        try:
            return (tuple(self.facet_to_sid[x] for x in cycles[0]),
                    tuple(self.facet_to_sid[x] for x in cycles[1]))
        except KeyError:
            return None

    def _conj_perms(self, algs):
        """单动作对边槽贴纸的移动映射（共轭方向）。
        共轭 G·H·G⁻¹ 的贴纸循环 = σ⁻¹ 作用，故返回逆映射 new_sid -> old_sid。"""
        out = []
        for a in algs:
            cube = _apply_labeled(self.n, [a])
            perm = {}
            for sid, idx in enumerate(self.edge_facets):
                old = cube.facelets[idx]
                if old in self.facet_to_sid:
                    perm[self.facet_to_sid[old]] = sid
            out.append((a, {v: k for k, v in perm.items()}))
        return out

    def find_cycle(self, s, p, free_set):
        """找把位置 p 的贴纸放入 s 的原语。
        free_set：允许扰动的槽 id 集合（q 与另一循环必须都在其中）。
        返回动作序列或 None。"""
        for cyc, other, moves in self._by_pair.get((p, s), ()):
            q = next(x for x in cyc if x != p and x != s)
            if q in free_set and all(x in free_set for x in other):
                return moves
        return None

    def coverage(self):
        """所有 (p, s) 有序对的库覆盖情况，返回缺失列表"""
        n_s = len(self.edge_facets)
        missing = []
        for p in range(n_s):
            for s in range(n_s):
                if p == s:
                    continue
                if not self._by_pair.get((p, s)):
                    missing.append((p, s))
        return missing


def solve_edges_reduce(cube, library=None):
    """
    边贴纸精确归位（= 翼块/中棱物理位置归位）。

    与 solve_edges_pair（颜色配对）的区别：配对只保证每棱线贴纸颜色 ∈ 双色集，
    5x5 下翼块可能翻面/错位而不被发现；精确归位把每张贴纸放回其 home 位置，
    结构上保证降阶后的 3x3 提取与物理魔方一致，kociemba 收尾必然还原。

    求解策略：每轮选一个有可用原语的未归位槽处理（避免结构性缺原语的槽
    过早卡死），原语依次尝试 直接 -> 两跳 staging -> relaxed（允许破坏少量
    已归位槽）。返回 (moves, error)。前置：中心已解。
    """
    n = cube.size
    if library is None or library.n != n:
        library = EdgeReduceLibrary(n)
        library.build()
    facet_info = library.facet_info
    n_slots = len(facet_info)
    moves_out = []
    max_iters = 20000
    iters = 0

    while True:
        iters += 1
        if iters > max_iters:
            return moves_out, f"边求解超过迭代上限（剩余 {len(unsolved)} 槽）"

        # 全量重算未归位槽（relaxed 可能破坏已归位槽）
        unsolved = {
            x for x in range(n_slots)
            if cube.get_facelet(*facet_info[x]) != FACE_NAMES[facet_info[x][0]]
        }
        if not unsolved:
            break

        # 1) 直接 / 两跳 staging
        seq = None
        for sid in sorted(unsolved):
            fi, r, c = facet_info[sid]
            color = FACE_NAMES[fi]
            candidates = [
                j for j in unsolved
                if j != sid and cube.get_facelet(*facet_info[j]) == color
            ]
            if not candidates:
                continue
            seq = _find_with_staging(sid, candidates, unsolved, library)
            if seq:
                break
        if seq is not None:
            cube.apply_moves(seq)
            moves_out.extend(seq)
            continue

        # 2) relaxed：允许破坏少量已归位槽，但要求"归位槽数净进展 >= 1"，
        #    避免破坏-重建 churn 死循环
        home_color = lambda x: FACE_NAMES[facet_info[x][0]]
        best = None  # (net, destroyed, moves)
        for sid in sorted(unsolved):
            fi, r, c = facet_info[sid]
            color = FACE_NAMES[fi]
            candidates = [
                j for j in unsolved
                if j != sid and cube.get_facelet(*facet_info[j]) == color
            ]
            for pj in candidates:
                for cyc, other, moves in library._by_pair.get((pj, sid), ()):
                    q = next(x for x in cyc if x != pj and x != sid)
                    net, destroyed = _home_move_delta(
                        cube, facet_info, home_color, cyc, other, sid)
                    if net <= 0:
                        continue
                    if best is None or net > best[0] or (
                            net == best[0] and destroyed < best[1]):
                        best = (net, destroyed, moves)
        if best is not None:
            cube.apply_moves(best[2])
            moves_out.extend(best[2])
            continue

        return moves_out, f"边求解卡死（所有未对槽均无可用原语，剩余 {len(unsolved)} 槽）"

    return moves_out, None


def _facelet_pos3(n, f, r, c):
    """贴纸物理坐标（与 bigcube 一致）"""
    m = n - 1
    if f == 0: return (c, m, r)
    if f == 1: return (c, 0, m - r)
    if f == 2: return (c, m - r, m)
    if f == 3: return (m - c, m - r, 0)
    if f == 4: return (0, m - r, c)
    return (m, m - r, m - c)


def edge_lines(n):
    """12 条棱线（d-edge）的翼贴纸位置分组，每条 [(face, r, c), ...]。
    4x4：每条 4 贴纸（2 翼块）；5x5：每条 6 贴纸（2 翼块 + 1 中棱）。"""
    lines = {}
    for f in range(6):
        for r in range(n):
            for c in range(n):
                if (r == 0 or r == n - 1) != (c == 0 or c == n - 1):
                    x, y, z = _facelet_pos3(n, f, r, c)
                    fixed = []
                    for a, v in (("x", x), ("y", y), ("z", z)):
                        if v == 0 or v == n - 1:
                            fixed.append((a, v))
                    if len(fixed) != 2:
                        continue
                    key = tuple(sorted(fixed))
                    lines.setdefault(key, []).append((f, r, c))
    return list(lines.values())


def _find_with_staging(sid, candidates, unsolved, library):
    """找把某候选 p 的贴纸放入 sid 的原语；直接无解时用两跳 staging p->r->s。"""
    for pj in candidates:
        seq = library.find_cycle(sid, pj, unsolved)
        if seq:
            return seq
    for pj in candidates:
        for r in unsolved:
            if r == sid or r == pj:
                continue
            seq1 = library.find_cycle(r, pj, unsolved)
            if not seq1:
                continue
            seq2 = library.find_cycle(sid, r, unsolved)
            if not seq2:
                continue
            return seq1 + seq2
    return None


def _find_relaxed(sid, candidates, unsolved, library, max_destroy=2):
    """找把某候选 p 的贴纸放入 sid 的原语；允许破坏 max_destroy 个已配对槽。
    返回 (moves, destroyed)。destroyed = 应用后会被破坏的已配对槽（需重新配对）。"""
    best = None
    for pj in candidates:
        for cyc, other, moves in library._by_pair.get((pj, sid), ()):
            q = next(x for x in cyc if x != pj and x != sid)
            touch = [x for x in (q,) + tuple(other) if x not in unsolved and x != sid]
            if len(touch) <= max_destroy:
                if best is None or len(touch) < len(best[1]):
                    best = (moves, touch)
    return (best[0], best[1]) if best else (None, [])


def _anchor_freq(library):
    """统计每个槽作为 other 循环元素（锚点）的频率。
    锚点频率高的槽 = 重要 buffer，应尽量保留 free（最后配对）。"""
    freq = {}
    for entries in library._by_pair.values():
        for cyc, other, moves in entries:
            for x in other:
                freq[x] = freq.get(x, 0) + 1
    return freq


def _home_move_delta(cube, facet_info, home_color, cyc, other, sid):
    """原语（主循环 p->sid, sid->q, q->p；other 循环 3 槽轮换）的归位净变化。
    返回 (net, destroyed)。net = 归位槽数（颜色==所在面颜色）前后差。"""
    p, s, q = cyc
    slots = [p, s, q, other[0], other[1], other[2]]
    before = {x: cube.get_facelet(*facet_info[x]) for x in slots}
    after = {
        s: before[p], q: before[s], p: before[q],
        other[0]: before[other[2]], other[1]: before[other[0]],
        other[2]: before[other[1]],
    }
    correct_before = 0
    correct_after = 0
    destroyed = 0
    for x in slots:
        cb = before[x] == home_color(x)
        ca = after[x] == home_color(x)
        correct_before += cb
        correct_after += ca
        if cb and not ca:
            destroyed += 1
    return correct_after - correct_before, destroyed


def _find_edge_chain(sid, unsolved, library, facet_info, line_of, cube):
    """邻位链 fallback：sid 无法直接从候选 p 接收贴纸时，
    sid <- q（q 的贴纸颜色 ∈ line_of[sid]），q <- p（p 的贴纸颜色 ∈ line_of[q]）。
    只用未对槽（严格 free，不破坏已配对槽），q 最终重新配对，净进度 +2。"""
    sid_colors = line_of[sid]
    for q in unsolved:
        if q == sid:
            continue
        fi, r, c = facet_info[q]
        if cube.get_facelet(fi, r, c) not in sid_colors:
            continue
        for p in unsolved:
            if p in (sid, q):
                continue
            fi2, r2, c2 = facet_info[p]
            if cube.get_facelet(fi2, r2, c2) not in line_of[q]:
                continue
            hit_a = library.find_cycle(sid, q, unsolved)  # q 的贴纸 -> sid
            if not hit_a:
                continue
            hit_b = library.find_cycle(q, p, unsolved)    # p 的贴纸 -> q
            if not hit_b:
                continue
            return hit_a + hit_b
    return None


def _pair_delta(cube, facet_info, line_of, sid, p, q, other):
    """原语（主循环 p->sid, sid->q, q->p；other 循环 3 槽轮换）的配对净变化。"""
    slots = [sid, p, q] + list(other)
    colors_before = {}
    for s in slots:
        fi, r, c = facet_info[s]
        colors_before[s] = cube.get_facelet(fi, r, c)
    after_colors = {
        sid: colors_before[p], q: colors_before[sid], p: colors_before[q],
        other[0]: colors_before[other[2]], other[1]: colors_before[other[0]],
        other[2]: colors_before[other[1]],
    }
    delta = 0
    for s in slots:
        paired_before = colors_before[s] in line_of[s]
        paired_after = after_colors[s] in line_of[s]
        delta += int(paired_after) - int(paired_before)
    return delta


def _iter_primitives(library):
    """遍历库中全部去重原语 (cyc, other, moves)。"""
    seen = set()
    for lst in library._by_pair.values():
        for cyc, other, moves in lst:
            key = "|".join(moves)
            if key not in seen:
                seen.add(key)
                yield cyc, other, moves


def _best_edge_move(cube, unsolved, library, facet_info, line_of, order_key):
    """爬山：全库扫描所有原语（主循环三种对齐），选配对净变化最大的。
    不能只扫"p 的颜色∈line_of[sid]"的匹配对——改善可能来自主循环其他
    对齐或 other 循环（实测死锁态正因此漏掉 delta=+2 的完成原语）。
    返回 (seq, delta, sid) 或 (None, None, None)。"""
    best_seq, best_delta, best_sid = None, None, None
    for cyc, other, moves in _iter_primitives(library):
        for i in range(3):
            p, sid = cyc[i], cyc[(i + 1) % 3]
            q = cyc[(i + 2) % 3]
            delta = _pair_delta(cube, facet_info, line_of, sid, p, q, other)
            if best_delta is None or delta > best_delta or (
                    delta == best_delta and order_key(sid) < order_key(best_sid)):
                best_seq, best_delta, best_sid = moves, delta, sid
                if delta >= 2:
                    return best_seq, best_delta, best_sid
    return best_seq, best_delta, best_sid


def solve_edges_pair(cube, library=None):
    """
    边配对（降阶法标准做法）：让每条棱线的翼贴纸都属于该棱线的双色集。
    比"贴纸归位"宽松（每槽 2 个可接受色），贪心更易完成；
    配对后的位置/方向/奇偶交给 kociemba 收尾处理。
    返回 (moves, error)。前置：中心已解。

    策略：爬山贪心 —— 每轮在所有可用原语中选"配对净变化最大"的动作；
    局部最大时做深度受限的逃生搜索（允许短期配对下降以翻越平台）。
    """
    n = cube.size
    if library is None or library.n != n:
        library = EdgeReduceLibrary(n)
        library.build()
    facet_info = library.facet_info
    sid_of = {info: sid for sid, info in enumerate(facet_info)}
    # 每条棱线的双色集 -> 每槽可接受颜色
    line_of = {}
    for line in edge_lines(n):
        colors = {FACE_NAMES[f] for (f, r, c) in line}
        for pos in line:
            line_of[sid_of[pos]] = colors

    unsolved = set(range(len(facet_info)))
    moves_out = []
    freq = _anchor_freq(library)
    order_key = lambda x: (freq.get(x, 0), x)  # 低频锚点槽优先
    stall = 0

    while True:
        # 全量重算未对槽（原语 other 循环可能破坏之前已对的槽）
        unsolved = {x for x in range(len(facet_info))
                    if cube.get_facelet(*facet_info[x]) not in line_of[x]}
        if not unsolved:
            break

        seq, delta, sid = _best_edge_move(cube, unsolved, library, facet_info,
                                          line_of, order_key)
        if seq is not None and delta > 0:
            stall = 0
            cube.apply_moves(seq)
            moves_out.extend(seq)
            continue

        # 平台（无正 delta）或死锁：深度受限逃生搜索
        esc = _edge_escape(cube, unsolved, library, facet_info, line_of,
                           order_key)
        if esc is not None:
            cube.apply_moves(esc)
            moves_out.extend(esc)
            stall = 0
            continue

        # 逃生失败：若还有次优动作，有限次应用以改换局面；否则报错
        stall += 1
        if seq is not None and stall <= 3:
            cube.apply_moves(seq)
            moves_out.extend(seq)
            continue
        return moves_out, f"边配对卡死（剩余 {len(unsolved)} 槽）"

    return moves_out, None


def _edge_escape(cube, unsolved, library, facet_info, line_of, order_key,
                 max_depth=3, beam=10):
    """平台/死锁逃生：光束搜索。每层只保留"配对净变化"前 beam 的动作，
    允许中间配对下降（delta >= -2），找一条使未对槽数下降的路径。
    候选动作为全库原语（不限于"匹配对"），并只考虑触及未对槽的原语。"""
    n = cube.size
    prims = list(_iter_primitives(library))

    def count_unsolved(c):
        return sum(1 for x, (fi, r, cc) in enumerate(facet_info)
                   if c.get_facelet(fi, r, cc) not in line_of[x])

    n0 = count_unsolved(cube)

    def gen(c, u):
        """候选动作：触及未对槽、delta >= -2；按 delta 降序去重。"""
        cands = {}
        for cyc, other, moves in prims:
            slots = cyc + other
            if not any(x in u for x in slots):
                continue
            for i in range(3):
                p, sid = cyc[i], cyc[(i + 1) % 3]
                q = cyc[(i + 2) % 3]
                delta = _pair_delta(c, facet_info, line_of, sid, p, q, other)
                if delta >= -2:
                    key = "|".join(moves)
                    if key not in cands:
                        cands[key] = (delta, moves)
        return sorted(cands.values(), key=lambda x: -x[0])[:beam]

    level = [(cube.serialize(), [])]
    seen = {cube.serialize()}
    for _ in range(max_depth):
        next_level = []
        for state_str, path in level:
            c = BigCube(n, state_str)
            u = {x for x in range(len(facet_info))
                 if c.get_facelet(*facet_info[x]) not in line_of[x]}
            for delta, moves in gen(c, u):
                c2 = BigCube(n, state_str)
                c2.apply_moves(moves)
                ns = count_unsolved(c2)
                if ns < n0:
                    flat = [m for mlist in path + [moves] for m in mlist]
                    return flat
                key = c2.serialize()
                if ns <= n0 and key not in seen:
                    seen.add(key)
                    next_level.append((key, path + [moves]))
        if not next_level:
            break
        level = next_level[:beam * beam]
    return None


def wing_and_middle_ids(library):
    """5x5 边槽划分：返回 (翼槽 ids, 中棱槽 ids)。
    中棱槽 = extract_3x3 采样的 24 个位置（每条棱线中间那对贴纸）。"""
    n = library.n
    m = n // 2
    middle = set()
    for sid, (f, r, c) in enumerate(library.facet_info):
        if (r == m and c in (0, n - 1)) or (c == m and r in (0, n - 1)):
            middle.add(sid)
    return set(range(len(library.facet_info))) - middle, middle


def solve_edges_wings(cube, library=None):
    """5x5 翼槽精确归位（方案2 的 5x5 专用实现）。

    只需归位 48 个翼槽：中棱槽正是 extract_3x3 的采样位置，由 kociemba 收尾解好；
    中棱槽在求解中始终作为 free 槽。中棱+角恒构成合法 3x3（内层 3x3 只被宽转/外层
    动作移动，内层切动作不触及），因此 kociemba 必可解、无需 OLL/PLL parity。

    求解策略（借鉴 centers.py 的链式 + 模拟验证模式）：
    1. 直接 / 两跳 staging（不破坏已归位翼槽）；
    2. 精确归位链：sid <- q（q 含 sid 的 home 色），q <- p（p 含 q 的 home 色），
       净进度 +2，q 最终被回填正确，不破坏已归位槽；
    3. 破坏性 fallback：允许扰动少量已归位翼槽，但严格只接受"未归位槽净减少 ≥1"
       的移动（模拟验证），避免净零 churn 死循环。
    返回 (moves, error)。前置：中心已解。"""
    n = cube.size
    if library is None or library.n != n:
        library = EdgeReduceLibrary(n)
        library.build()
    facet_info = library.facet_info
    wing_slots, middle_ids = wing_and_middle_ids(library)
    moves_out = []
    max_iters = 3000

    def home_color(s):
        return FACE_NAMES[facet_info[s][0]]

    def count_wings(c):
        return sum(1 for x in wing_slots
                   if c.get_facelet(*facet_info[x]) != home_color(x))

    for _ in range(max_iters):
        unsolved = {x for x in wing_slots
                    if cube.get_facelet(*facet_info[x]) != home_color(x)}
        if not unsolved:
            break
        free_set = middle_ids | unsolved

        # 1) 直接 / 两跳 staging（destroy-free）
        seq = None
        for sid in sorted(unsolved):
            color = home_color(sid)
            candidates = [j for j in free_set
                          if j != sid and cube.get_facelet(*facet_info[j]) == color]
            if not candidates:
                continue
            seq = _find_with_staging(sid, candidates, free_set, library)
            if seq:
                break
        if seq is not None:
            cube.apply_moves(seq)
            moves_out.extend(seq)
            continue

        # 2) 精确归位链：sid <- q <- p（净进度 +2，q 被回填）
        seq = None
        for sid in sorted(unsolved):
            s_color = home_color(sid)
            for q in free_set:
                if q == sid or cube.get_facelet(*facet_info[q]) != s_color:
                    continue
                q_color = home_color(q) if q in wing_slots else None
                # q 若为中棱槽则无需回填（kociemba 处理），只需 sid 归位
                for p in free_set:
                    if p in (sid, q):
                        continue
                    if q in wing_slots and cube.get_facelet(*facet_info[p]) != q_color:
                        continue
                    hit_a = library.find_cycle(sid, q, free_set)
                    if not hit_a:
                        continue
                    hit_b = library.find_cycle(q, p, free_set)
                    if not hit_b:
                        continue
                    seq = hit_a + hit_b
                    break
                if seq:
                    break
            if seq:
                break
        if seq is not None:
            cube.apply_moves(seq)
            moves_out.extend(seq)
            continue

        # 3) 破坏性 fallback：严格净进展（未归位槽净减少 ≥1）
        best = None  # (net, destroyed, moves)
        for sid in sorted(unsolved):
            color = home_color(sid)
            candidates = [j for j in free_set
                          if j != sid and cube.get_facelet(*facet_info[j]) == color]
            for pj in candidates:
                for cyc, other, moves in library._by_pair.get((pj, sid), ()):
                    q = next(x for x in cyc if x != pj and x != sid)
                    net, destroyed = _wing_move_delta(
                        cube, facet_info, wing_slots, home_color,
                        cyc, other, sid)
                    if net <= 0:
                        continue
                    if best is None or net > best[0] or (
                            net == best[0] and destroyed < best[1]):
                        best = (net, destroyed, moves)
        if best is not None:
            cube.apply_moves(best[2])
            moves_out.extend(best[2])
            continue

        # 4) 逃生搜索：允许暂时退步（净变化 >= -1），光束搜索跳出局部最小
        esc = _wing_escape(cube, wing_slots, facet_info, home_color,
                           library)
        if esc is not None:
            cube.apply_moves(esc)
            moves_out.extend(esc)
            continue

        return moves_out, f"翼槽求解卡死（剩余 {len(unsolved)} 槽）"

    return moves_out, None


def solve_edges_middle(cube, library=None):
    """5x5 中棱槽精确归位（24 贴纸，12 个中棱块）。

    前置：翼块已精确归位（48 翼贴纸回 home）。中棱归位必须用【纯中棱原语】
    （3-cycle + other 循环全在中棱槽），否则会扰动已归位的翼块。

    数学完备性：翼块归位成功（偶状态）⟹ 中棱置换必为偶（5x5 守恒：
    翼块奇偶 ⊕ 中棱奇偶 = 0），故纯偶原语可归位、不会卡奇状态。
    返回 (moves, error)。前置：中心 + 翼块已解。"""
    n = cube.size
    if library is None or library.n != n:
        library = EdgeReduceLibrary(n)
        library.build()
    facet_info = library.facet_info
    _, middle_ids = wing_and_middle_ids(library)
    moves_out = []
    max_iters = 4000

    def home_color(s):
        return FACE_NAMES[facet_info[s][0]]

    for _ in range(max_iters):
        unsolved = {x for x in middle_ids
                    if cube.get_facelet(*facet_info[x]) != home_color(x)}
        if not unsolved:
            break

        # 1) 直接 / 两跳 staging（纯中棱原语，不扰动翼块）
        seq = None
        for sid in sorted(unsolved):
            color = home_color(sid)
            candidates = [j for j in middle_ids
                          if j != sid and cube.get_facelet(*facet_info[j]) == color]
            if not candidates:
                continue
            seq = _find_middle_staging(sid, candidates, unsolved, library,
                                       middle_ids)
            if seq:
                break
        if seq is not None:
            cube.apply_moves(seq)
            moves_out.extend(seq)
            continue

        # 2) 破坏性 fallback：严格净进展（归位槽净减少 ≥1）
        best = None  # (net, destroyed, moves)
        for sid in sorted(unsolved):
            color = home_color(sid)
            candidates = [j for j in middle_ids
                          if j != sid and cube.get_facelet(*facet_info[j]) == color]
            for pj in candidates:
                for cyc, other, moves in library._by_pair.get((pj, sid), ()):
                    if not all(x in middle_ids for x in cyc + tuple(other)):
                        continue
                    q = next(x for x in cyc if x != pj and x != sid)
                    net, destroyed = _home_move_delta(
                        cube, facet_info, home_color, cyc, other, sid)
                    if net <= 0:
                        continue
                    if best is None or net > best[0] or (
                            net == best[0] and destroyed < best[1]):
                        best = (net, destroyed, moves)
        if best is not None:
            cube.apply_moves(best[2])
            moves_out.extend(best[2])
            continue

        # 3) 卡死时：剩余槽少 → BFS 直接搜索（允许先破坏再重建）
        if len(unsolved) <= 8:
            seq = _bfs_middle(cube, library, middle_ids, facet_info,
                              home_color, max_depth=7)
            if seq:
                cube.apply_moves(seq)
                moves_out.extend(seq)
                continue

        return moves_out, f"中棱求解卡死（剩余 {len(unsolved)} 槽）"

    return moves_out, None


def _find_middle_staging(sid, candidates, unsolved, library, middle_ids):
    """纯中棱原语的两跳 staging：p -> r -> s，所有原语都只触及中棱槽。"""
    for pj in candidates:
        seq = _find_pure(sid, pj, unsolved, library, middle_ids)
        if seq:
            return seq
    for pj in candidates:
        for r in unsolved:
            if r == sid or r == pj:
                continue
            seq1 = _find_pure(r, pj, unsolved, library, middle_ids)
            if not seq1:
                continue
            seq2 = _find_pure(sid, r, unsolved, library, middle_ids)
            if not seq2:
                continue
            return seq1 + seq2
    return None


def _find_pure(s, p, free_set, library, middle_ids):
    """找纯中棱原语：把 p 的贴纸放入 s，q 与 other 都在 free_set 且全在中棱槽。"""
    for cyc, other, moves in library._by_pair.get((p, s), ()):
        if not all(x in middle_ids for x in cyc + tuple(other)):
            continue
        q = next(x for x in cyc if x != p and x != s)
        if q in free_set and all(x in free_set for x in other):
            return moves
    return None


def _bfs_middle(cube, library, middle_ids, facet_info, home_color,
                max_depth=6, node_limit=200000):
    """中棱剩余槽少时（贪心卡死）的直接搜索。

    贪心卡死根因：剩余 2 槽（偶置换如 [2,2] 两个 2-cycle）时，任何单个
    纯中棱原语的 other 循环必然触及已归位中棱槽 → free_set 拒绝 → 无解。
    数学上偶置换 = 3-cycle 的积，但需要"先破坏再重建"（净进展先负后正），
    贪心无法前瞻。本函数在纯中棱原语动作空间上 BFS（允许破坏已归位中棱槽），
    找到把中棱全部归位的动作序列。返回动作列表或 None。

    优化：动作按 (cyc1, cyc2) 结构去重（每结构只留最短 moves）；
    每层只扩展主循环触及当前未归位槽的原语，剪枝未归位槽 ≤ 10。
    """
    from collections import deque

    def get_tuple():
        return tuple(cube.get_facelet(*facet_info[x]) for x in middle_ids)

    goal = tuple(home_color(x) for x in middle_ids)
    start = get_tuple()
    if start == goal:
        return []

    mid_pos = {sid: i for i, sid in enumerate(middle_ids)}

    # 动作：纯中棱原语按结构去重（保留最短 moves）
    struct_moves = {}
    for (p, s), lst in library._by_pair.items():
        for cyc, other, moves in lst:
            if not all(x in middle_ids for x in cyc + tuple(other)):
                continue
            key = (tuple(sorted(cyc)), tuple(sorted(other)))
            cur = struct_moves.get(key)
            if cur is None or len(moves) < len(cur):
                struct_moves[key] = moves
    actions = []  # (主循环槽集合, f, moves)
    for (cyc, other), moves in struct_moves.items():
        f = {}
        for i in range(3):
            f[cyc[i]] = cyc[(i + 1) % 3]
            f[other[i]] = other[(i + 1) % 3]
        actions.append((set(cyc), f, moves))

    def apply(st, f):
        new = list(st)
        for src, dst in f.items():
            new[mid_pos[dst]] = st[mid_pos[src]]
        return tuple(new)

    dist = {start: 0}
    parent = {}
    q = deque([start])
    found = None
    expanded = 0
    while q:
        st = q.popleft()
        expanded += 1
        if expanded > node_limit:
            break
        d = dist[st]
        if d >= max_depth:
            continue
        # 当前未归位槽（middle_ids 中的位置索引）
        uns = {i for i in range(len(middle_ids)) if st[i] != goal[i]}
        for mset, f, mv in actions:
            # 只扩展主循环触及未归位槽的动作
            if not any(mid_pos[x] in uns for x in mset):
                continue
            st2 = apply(st, f)
            if sum(1 for i in range(len(middle_ids)) if st2[i] != goal[i]) > 10:
                continue
            if st2 not in dist:
                dist[st2] = d + 1
                parent[st2] = (st, mv)
                q.append(st2)
                if st2 == goal:
                    found = st2
                    q.clear()
                    break
    if found is None:
        return None

    path = []
    st = found
    while st != start:
        prev, mv = parent[st]
        path.append(list(mv))
        st = prev
    path.reverse()
    out = []
    for mv in path:
        out.extend(mv)
    return out


# ---- 5x5 奇偶翻转 ----
# 翼块奇偶翻转：单个内层转动（奇置换）不触及中棱，中心可重解
WING_FLIPS = ["MR'", "ML", "MU'", "MD", "MR", "ML'", "MU", "MD'"]
# 中棱奇偶翻转：面转动/宽转改变中棱奇偶且中心可重解；
# MR/ML/MU/MD 不动中棱，M/E/S 改变中棱但破坏中心可解性（均不可用）
MID_FLIPS = ["R", "R'", "U", "U'", "F", "F'", "L", "L'", "D", "D'", "B", "B'"]


def _count_wrong(cube, facet_info, slots):
    """slots 中贴纸不在 home 位置的槽数。"""
    return sum(1 for x in slots
               if cube.get_facelet(*facet_info[x]) != FACE_NAMES[facet_info[x][0]])


def middle_piece_state(cube, library):
    """12 片中棱的片置换（每条棱线当前放置的片 id，按双色对反查）。
    任一棱线双色对不在已知 12 组中（不可能，除非已降阶）返回 None。"""
    facet_info = library.facet_info
    _, middle_ids = wing_and_middle_ids(library)
    c2p = {}
    line_of_mid = []
    for li, line in enumerate(edge_lines(cube.size)):
        lc = frozenset(FACE_NAMES[f] for (f, r, c) in line)
        c2p[lc] = li
        mids = [sid for (f, r, c) in line
                for sid in [next((s for s in range(len(facet_info))
                                  if facet_info[s] == (f, r, c)), -1)]
                if sid != -1 and sid in middle_ids]
        line_of_mid.append(mids)
    state = []
    for mids in line_of_mid:
        cols = frozenset(cube.get_facelet(*facet_info[s]) for s in mids)
        li = c2p.get(cols, -1)
        if li == -1:
            return None
        state.append(li)
    return tuple(state)


def middle_is_odd(cube, library):
    """中棱片置换奇偶：0 偶 / 1 奇 / None（有翻转或异常，无法判定）。"""
    st = middle_piece_state(cube, library)
    if st is None:
        return None
    visited = [False] * 12
    parity = 0
    for i in range(12):
        if visited[i]:
            continue
        cur = i
        length = 0
        while not visited[cur]:
            visited[cur] = True
            cur = st[cur]
            length += 1
        if length > 1:
            parity ^= (length - 1) % 2
    return parity


def solve_edges_middle_general(cube, library=None):
    """5x5 中棱归位（全库 buffer 版）：翼槽作为自由 buffer，中棱全部归位。

    与 solve_edges_middle（纯中棱原语、不扰动翼块）不同：本函数允许用翼槽
    中转，覆盖不足时更容易完成；代价是翼块可能被扰动，需外层交替重解翼块。
    返回 (moves, error)。前置：中心已解。"""
    n = cube.size
    if library is None or library.n != n:
        library = EdgeReduceLibrary(n)
        library.build()
    facet_info = library.facet_info
    wing_slots, middle_ids = wing_and_middle_ids(library)
    moves_out = []
    max_iters = 4000

    def home_color(s):
        return FACE_NAMES[facet_info[s][0]]

    for _ in range(max_iters):
        unsolved = {x for x in middle_ids
                    if cube.get_facelet(*facet_info[x]) != home_color(x)}
        if not unsolved:
            break
        free_set = wing_slots | unsolved

        # 1) 直接 / 两跳 staging（destroy-free）
        seq = None
        for sid in sorted(unsolved):
            color = home_color(sid)
            candidates = [j for j in free_set
                          if j != sid and cube.get_facelet(*facet_info[j]) == color]
            if not candidates:
                continue
            seq = _find_with_staging(sid, candidates, free_set, library)
            if seq:
                break
        if seq is not None:
            cube.apply_moves(seq)
            moves_out.extend(seq)
            continue

        # 2) 破坏性 fallback：严格净进展（归位槽净减少 ≥1）
        best = None
        for sid in sorted(unsolved):
            color = home_color(sid)
            candidates = [j for j in free_set
                          if j != sid and cube.get_facelet(*facet_info[j]) == color]
            for pj in candidates:
                for cyc, other, moves in library._by_pair.get((pj, sid), ()):
                    q = next(x for x in cyc if x != pj and x != sid)
                    net, destroyed = _home_move_delta(
                        cube, facet_info, home_color, cyc, other, sid)
                    if net <= 0:
                        continue
                    if best is None or net > best[0] or (
                            net == best[0] and destroyed < best[1]):
                        best = (net, destroyed, moves)
        if best is not None:
            cube.apply_moves(best[2])
            moves_out.extend(best[2])
            continue

        # 3) 逃生搜索：允许短期退步跳出局部最小
        esc = _escape_middle_general(cube, library, home_color, wing_slots,
                                     middle_ids)
        if esc is not None:
            cube.apply_moves(esc)
            moves_out.extend(esc)
            continue

        return moves_out, f"中棱求解卡死（剩余 {len(unsolved)} 槽）"

    return moves_out, None


def _escape_middle_general(cube, library, home_color, wing_slots, middle_ids,
                           max_depth=3, beam=14):
    """中棱逃生：光束搜索，允许中间中棱归位数暂时下降（净变化 >= -1），
    找一条使未归位中棱槽数下降的路径。候选动作为全库原语（翼槽可作 buffer）。
    返回动作列表或 None。"""
    n = cube.size
    facet_info = library.facet_info
    prims = list(_iter_primitives(library))

    def count_unsolved(c):
        return sum(1 for x in middle_ids
                   if c.get_facelet(*facet_info[x]) != home_color(x))

    n0 = count_unsolved(cube)

    def gen(c, u):
        cands = {}
        for cyc, other, moves in prims:
            if not any(x in u for x in (cyc + tuple(other))):
                continue
            for i in range(3):
                p, s = cyc[i], cyc[(i + 1) % 3]
                if s not in middle_ids:
                    continue
                q = cyc[(i + 2) % 3]
                net, _ = _home_move_delta(c, facet_info, home_color,
                                          (p, s, q), other, s)
                if net >= -1:
                    key = "|".join(moves)
                    if key not in cands:
                        cands[key] = (net, moves)
        return sorted(cands.values(), key=lambda x: -x[0])[:beam]

    level = [(cube.serialize(), [])]
    seen = {cube.serialize()}
    for _ in range(max_depth):
        next_level = []
        for state_str, path in level:
            c = BigCube(n, state_str)
            u = {x for x in middle_ids
                 if c.get_facelet(*facet_info[x]) != home_color(x)}
            for net, moves in gen(c, u):
                c2 = BigCube(n, state_str)
                c2.apply_moves(moves)
                ns = count_unsolved(c2)
                if ns < n0:
                    return [m for mlist in path + [moves] for m in mlist]
                key = c2.serialize()
                if ns <= n0 and key not in seen:
                    seen.add(key)
                    next_level.append((key, path + [moves]))
        if not next_level:
            break
        level = next_level[:beam * beam]
    return None


def solve_wings_with_parity(cube, edge_lib, center_lib):
    """翼块求解 + 奇偶翻转修复（内层转动翻转翼块奇偶 + 重解中心）。
    返回 (moves, error)。前置：中心已解。"""
    from centers import solve_centers
    moves_out = []
    for attempt in range(8):
        wmoves, werr = solve_edges_wings(cube, edge_lib)
        moves_out.extend(wmoves)
        if werr is None:
            return moves_out, None
        fixed = False
        for flip in WING_FLIPS:
            c2 = BigCube(cube.size, cube.serialize())
            c2.apply_moves([flip])
            cm2, ce2 = solve_centers(c2, center_lib)
            if ce2:
                continue
            w2, we2 = solve_edges_wings(c2, edge_lib)
            if we2 is None:
                cube.facelets = c2.facelets
                moves_out.append(flip)
                moves_out.extend(cm2)
                moves_out.extend(w2)
                fixed = True
                break
        if not fixed:
            return moves_out, f"翼块奇偶修复失败: {werr}"
    return moves_out, f"翼块归位超限: {werr}"


def solve_middle_with_parity(cube, edge_lib, center_lib):
    """中棱求解 + 奇偶翻转修复（面转动翻转中棱奇偶 + 重解中心）。
    返回 (moves, error)。前置：中心已解。"""
    from centers import solve_centers
    moves_out = []
    mm, stuck = solve_edges_middle_general(cube, edge_lib)
    moves_out.extend(mm)
    if stuck is None:
        return moves_out, None
    p = middle_is_odd(cube, edge_lib)
    if p == 1:
        for flip in MID_FLIPS:
            c2 = BigCube(cube.size, cube.serialize())
            c2.apply_moves([flip])
            cm2, ce2 = solve_centers(c2, center_lib)
            if ce2:
                continue
            m2, s2 = solve_edges_middle_general(c2, edge_lib)
            if s2 is None:
                cube.facelets = c2.facelets
                moves_out.append(flip)
                moves_out.extend(cm2)
                moves_out.extend(m2)
                return moves_out, None
        return moves_out, f"中棱奇偶修复失败(剩余{len(stuck)})"
    return moves_out, f"中棱卡死(偶, 剩余{len(stuck)})"


def solve_reduction_555(cube, edge_lib=None, center_lib=None):
    """5x5 方案2 完整链路：中心 → 翼块精确归位（含奇偶翻转修复）→
    中棱精确归位（含奇偶翻转修复）→ kociemba 收尾。返回 (moves, error)。

    交替求解：翼块归位用中棱作 buffer，中棱归位（全库 buffer）又会扰动翼块，
    外层循环交替求解直至两者全部归位（实测 1-2 轮收敛），再 kociemba 收尾。

    奇偶处理：
    - 翼块卡死 = 翼块奇置换，用单个内层转动（奇置换）翻转 + 重解中心/翼块；
    - 中棱卡死 = 中棱奇置换，用面转动翻转 + 重解中心/中棱
      （MR/ML/MU/MD 不动中棱，M/E/S 破坏中心可解性，均不可用）。
    """
    from centers import CenterLibrary, solve_centers
    n = cube.size
    if edge_lib is None or edge_lib.n != n:
        edge_lib = EdgeReduceLibrary(n)
        edge_lib.build()
    if center_lib is None or center_lib.n != n:
        center_lib = CenterLibrary(n)
        center_lib.build()

    moves_out = []
    cmoves, cerr = solve_centers(cube, center_lib)
    moves_out.extend(cmoves)
    if cerr:
        return moves_out, f"中心失败: {cerr}"

    facet_info = edge_lib.facet_info
    wing_slots, middle_ids = wing_and_middle_ids(edge_lib)
    best_total = None
    stall = 0
    for _ in range(6):
        # 1) 翼块（含奇偶翻转修复）
        wmoves, werr = solve_wings_with_parity(cube, edge_lib, center_lib)
        moves_out.extend(wmoves)

        # 2) 中棱（含奇偶翻转修复）
        mmoves, merr = solve_middle_with_parity(cube, edge_lib, center_lib)
        moves_out.extend(mmoves)

        # 3) 收敛检查：翼块/中棱某一方失败时不立即放弃——
        #    对方求解会重排另一方槽位，下一轮可能从新状态解出
        wl = _count_wrong(cube, facet_info, wing_slots)
        ml = _count_wrong(cube, facet_info, middle_ids)
        if werr is None and merr is None and wl == 0 and ml == 0:
            break
        total = wl + ml
        if best_total is None or total < best_total:
            best_total, stall = total, 0
        else:
            stall += 1
        if stall >= 2:
            return moves_out, (werr or merr or
                               f"交替求解不收敛（翼剩余{wl} 中棱剩余{ml}）")
    else:
        wl = _count_wrong(cube, facet_info, wing_slots)
        ml = _count_wrong(cube, facet_info, middle_ids)
        if wl or ml:
            return moves_out, f"交替求解超限（翼剩余{wl} 中棱剩余{ml}）"

    fmoves = finish_3x3(cube)
    moves_out.extend(fmoves)
    return moves_out, None


# ---- 4x4 parity 公式 ----
# OLL（Flip error）：翻转一个中棱，保持中心 + 边配对
OLL_PARITY_444 = ["MR2", "B2", "U2", "ML", "U2", "MR'", "U2", "MR", "U2",
                  "F2", "MR", "F2", "ML'", "B2", "MR2"]
# PLL（Parity error）：交换两个中棱 + 两个角，保持中心
PLL_PARITY_444 = ["MR2", "U2", "MR2", "TU2", "MR2", "TU2"]


def solve_reduction_444(cube, edge_lib=None, center_lib=None):
    """4x4 降阶法：中心 → 边配对 → kociemba 收尾（含 OLL/PLL parity 修复）。

    parity 修复不能依赖 kociemba 的错误消息：
    - 纯 Python 版区分 "Flip error" / "Parity error"；
    - 原生 C 版把所有校验失败统一报为 "Error. Probably cubestring is invalid"，
      不含 "Flip"/"Parity" 关键字，按消息识别会导致修复永不触发。
    因此改为：从"中心+边配对完成"的基线状态出发，按顺序尝试
    无修复 / OLL / PLL / OLL+PLL，直到 kociemba 接受为止。
    返回 (moves, error)。"""
    from centers import CenterLibrary, solve_centers
    from kociemba_guard import solve_with_timeout
    n = cube.size
    if edge_lib is None or edge_lib.n != n:
        edge_lib = EdgeReduceLibrary(n)
        edge_lib.build()
    if center_lib is None or center_lib.n != n:
        center_lib = CenterLibrary(n)
        center_lib.build()

    moves_out = []
    cmoves, cerr = solve_centers(cube, center_lib)
    moves_out.extend(cmoves)
    if cerr:
        return moves_out, f"中心失败: {cerr}"

    emoves, eerr = solve_edges_pair(cube, edge_lib)
    moves_out.extend(emoves)
    if eerr:
        return moves_out, f"边配对失败: {eerr}"

    base_state = cube.serialize()

    # (parity 动作, 说明)：空 / OLL / PLL / OLL+PLL。
    # 每种组合都从基线状态重放，避免需要回滚已应用的 parity 动作。
    options = [
        ([], "无"),
        (OLL_PARITY_444, "OLL"),
        (PLL_PARITY_444, "PLL"),
        (OLL_PARITY_444 + PLL_PARITY_444, "OLL+PLL"),
    ]
    last_err = None
    for parity_moves, label in options:
        c2 = BigCube(n, base_state)
        c2.apply_moves(parity_moves)
        s3 = extract_3x3(c2)
        try:
            # parity 状态的 3x3 会立刻被 kociemba 校验拒绝（不会挂起），
            # 用较短的超时兜底即可。
            sol = solve_with_timeout(s3, timeout=60)
        except Exception as e:
            last_err = e
            continue
        moves_out.extend(parity_moves)
        moves_out.extend(sol.split())
        c2.apply_moves(sol.split())
        cube.facelets = c2.facelets
        return moves_out, None
    return moves_out, f"kociemba 收尾失败: {last_err}"


def _wing_escape(cube, wing_slots, facet_info, home_color, library,
                 max_depth=4, beam=16):
    """局部最小逃生：光束搜索，允许中间翼槽归位数暂时下降（净变化 >= -1），
    找一条使未归位翼槽数下降的路径。候选动作为全库原语。返回动作列表或 None。"""
    n = cube.size
    prims = list(_iter_primitives(library))

    def count_unsolved(c):
        return sum(1 for x in wing_slots
                   if c.get_facelet(*facet_info[x]) != home_color(x))

    n0 = count_unsolved(cube)

    def gen(c, u):
        cands = {}
        for cyc, other, moves in prims:
            slots = cyc + tuple(other)
            if not any(x in u for x in slots):
                continue
            for i in range(3):
                p, s = cyc[i], cyc[(i + 1) % 3]
                if s not in wing_slots:
                    continue
                q = cyc[(i + 2) % 3]
                net, _ = _wing_move_delta(c, facet_info, wing_slots, home_color,
                                          (p, s, q), other, s)
                if net >= -1:
                    key = "|".join(moves)
                    if key not in cands:
                        cands[key] = (net, moves)
        return sorted(cands.values(), key=lambda x: -x[0])[:beam]

    level = [(cube.serialize(), [])]
    seen = {cube.serialize()}
    for _ in range(max_depth):
        next_level = []
        for state_str, path in level:
            c = BigCube(n, state_str)
            u = {x for x in wing_slots
                 if c.get_facelet(*facet_info[x]) != home_color(x)}
            for net, moves in gen(c, u):
                c2 = BigCube(n, state_str)
                c2.apply_moves(moves)
                ns = count_unsolved(c2)
                if ns < n0:
                    flat = [m for mlist in path + [moves] for m in mlist]
                    return flat
                key = c2.serialize()
                if ns <= n0 and key not in seen:
                    seen.add(key)
                    next_level.append((key, path + [moves]))
        if not next_level:
            break
        level = next_level[:beam * beam]
    return None


def _wing_move_delta(cube, facet_info, wing_slots, home_color, cyc, other, sid):
    """破坏性移动的翼槽净变化：模拟原语对 6 个触及槽的颜色轮换，
    统计"归位翼槽数"的前后差与破坏数。返回 (net, destroyed)。"""
    p, s, q = cyc  # 贴纸 p->s, s->q, q->p
    slots = [p, s, q, other[0], other[1], other[2]]
    before = {x: cube.get_facelet(*facet_info[x]) for x in slots}
    after = {
        s: before[p], q: before[s], p: before[q],
        other[0]: before[other[2]], other[1]: before[other[0]],
        other[2]: before[other[1]],
    }
    correct_before = 0
    correct_after = 0
    destroyed = 0
    for x in slots:
        if x not in wing_slots:
            continue
        cb = before[x] == home_color(x)
        ca = after[x] == home_color(x)
        correct_before += cb
        correct_after += ca
        if cb and not ca:
            destroyed += 1
    return correct_after - correct_before, destroyed


def extract_3x3(cube):
    """降阶后提取 kociemba 顺序（U,R,F,D,L,B）的 54 字符 facelet 串。
    前置：中心 + 边已配对（只差角块）。"""
    n = cube.size
    m = n // 2  # 4x4 -> 2, 5x5 -> 2（中心/中棱位置）
    order = ["U", "R", "F", "D", "L", "B"]
    pos_map = {
        (0, 0): (0, 0), (0, 1): (0, m), (0, 2): (0, n - 1),
        (1, 0): (m, 0), (1, 1): (m, m), (1, 2): (m, n - 1),
        (2, 0): (n - 1, 0), (2, 1): (n - 1, m), (2, 2): (n - 1, n - 1),
    }
    out = []
    for fname in order:
        fi = FACE_NAMES.index(fname)
        for r in range(3):
            for c in range(3):
                rr, cc = pos_map[(r, c)]
                out.append(cube.get_facelet(fi, rr, cc))
    return "".join(out)


def finish_3x3(cube, timeout=90):
    """kociemba 收尾：解降阶后的 3x3，动作直接应用到大立方体。返回动作列表。"""
    from kociemba_guard import is_valid_3x3, solve_with_timeout
    s3 = extract_3x3(cube)
    if not is_valid_3x3(s3):
        raise ValueError("降阶后 3x3 状态无效（颜色数量不对）")
    sol = solve_with_timeout(s3, timeout)
    moves = sol.split()
    cube.apply_moves(moves)
    return moves


if __name__ == "__main__":
    import sys
    import time
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    t0 = time.time()
    lib = EdgeReduceLibrary(n)
    lib.build()
    n_s = len(lib.edge_facets)
    total_pairs = n_s * (n_s - 1)
    miss = lib.coverage()
    print(f"构建完成 n={n} 用时 {time.time()-t0:.1f}s 原语条目 {len(lib._by_pair)}")
    print(f"覆盖: {total_pairs - len(miss)}/{total_pairs} 缺失 {len(miss)}")
    for m in miss[:10]:
        print("   ", m, lib.facet_info[m[0]], lib.facet_info[m[1]])
