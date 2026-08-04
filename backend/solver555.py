"""
5x5 Rubik's Cube solver — 降阶法（中心 -> 边 -> 角，全部 3-cycle 贪心）。

5x5 方案2（块级精确归位）：
1. solve_centers                 —— 中心归位
2. 翼块精确归位（含奇偶翻转修复） —— 48 翼槽全归位，卡死时内层转动翻转奇偶
3. 中棱精确归位（含奇偶翻转修复） —— 全库 buffer，卡死时面转动翻转奇偶
4. extract_3x3 + kociemba       —— 降阶后是合法 3x3，kociemba 收尾

原语库优先从 cache/edger5.pkl 加载（预生成），缺失时才现场构建。
"""

import os
import pickle
import threading

from bigcube import BigCube
from centers import CenterLibrary
from edges_reduce import EdgeReduceLibrary, solve_reduction_555

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
        if 5 not in _CACHE:
            libc = _load_lib("center5")
            if libc is None or libc.n != 5:
                libc = _build_and_save("center5", CenterLibrary(5))
            libe = _load_lib("edger5")
            if libe is None or libe.n != 5:
                libe = _build_and_save("edger5", EdgeReduceLibrary(5))
            _CACHE[5] = (libc, libe)
        return _CACHE[5]


def solve_555(state_str):
    """
    Solve a 5x5 cube using reduction method.
    state_str: 150-character facelet string, order U, F, R, D, B, L
    Returns: list of moves
    """
    if len(state_str) != 150:
        raise ValueError(f"State string must be 150 characters, got {len(state_str)}")

    cube = BigCube(5, state_str)
    libc, libe = _get_libs()

    moves, err = solve_reduction_555(cube, libe, libc)
    if err:
        raise ValueError(err)

    if not cube.is_solved():
        raise ValueError("求解结果未能还原魔方")

    return moves
