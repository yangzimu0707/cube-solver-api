"""
4x4 Rubik's Cube solver — 降阶法（中心 -> 边 -> 角，全部 3-cycle 贪心）。

4x4 降阶链路：
1. solve_centers                 —— 中心归位
2. solve_edges_pair              —— 边配对（每条棱线双色对齐）
3. extract_3x3 + kociemba       —— 降阶后按 3x3 处理；
   kociemba 拒绝时按错误类型修复：
   - Flip error   -> 应用 OLL parity（翻转一个中棱，保持中心+边配对）
   - Parity error -> 应用 PLL parity（交换两个中棱+两个角，保持中心）

原语库优先从 cache/edger4.pkl 加载（预生成），缺失时才现场构建。
"""

import os
import pickle
import threading

from bigcube import BigCube
from centers import CenterLibrary
from edges_reduce import (EdgeReduceLibrary, solve_reduction_444,
                          short_solve, simplify_moves)

_lock = threading.Lock()
_CACHE = {}
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")


def _load_lib(name):
    """从 cache/ 加载 pickle 库；不存在或损坏返回 None。"""
    path = os.path.join(_CACHE_DIR, name + ".pkl")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def _build_and_save(name, lib):
    lib.build()
    try:
        path = os.path.join(_CACHE_DIR, name + ".pkl")
        with open(path, "wb") as f:
            pickle.dump(lib, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        pass
    return lib


def _get_libs():
    """返回 (中心库, 边降阶库)，优先从缓存加载。"""
    with _lock:
        if 4 not in _CACHE:
            libc = _load_lib("center4")
            if libc is None or libc.n != 4:
                libc = _build_and_save("center4", CenterLibrary(4))
            libe = _load_lib("edger4")
            if libe is None or libe.n != 4:
                libe = _build_and_save("edger4", EdgeReduceLibrary(4))
            _CACHE[4] = (libc, libe)
        return _CACHE[4]


def solve_444(state_str):
    """
    Solve a 4x4 cube using reduction method.
    state_str: 96-character facelet string, order U, F, R, D, B, L
    Returns: list of moves
    """
    if len(state_str) != 96:
        raise ValueError(f"State string must be 96 characters, got {len(state_str)}")

    cube = BigCube(4, state_str)

    # 快速路径：近已解状态（如一步/两步/三步打乱）直接小深度求解
    short = short_solve(cube, max_depth=3)
    if short is not None:
        return short

    libc, libe = _get_libs()

    moves, err = solve_reduction_444(cube, libe, libc)
    if err:
        raise ValueError(err)

    if not cube.is_solved():
        raise ValueError("求解结果未能还原魔方")

    # 动作化简：合并相邻同基底动作
    return simplify_moves(moves)
