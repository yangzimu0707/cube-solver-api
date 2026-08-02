"""
4x4 Rubik's Cube solver — 降阶法（中心 -> 边 -> 角，全部 3-cycle 贪心）。

不再依赖 Kociemba：bigcube 模型（与前端 App 转层逻辑一致）存在拆块现象，
降阶后的角块在 3x3 意义上不保证合法，Kociemba 无法求解。
改用与 centers/edges 相同的"环对易子 3-cycle 原语 + 颜色驱动贪心"直接解角块，
最终以 cube.is_solved()（每面单色）验证还原。

原语库优先从 cache/*.pkl 加载（由 build_cache.py 预生成），
避免 Render 免费实例 60s 请求限制内无法完成首次构建；缺失时才现场构建。
"""

import os
import pickle
import threading

from bigcube import BigCube
from centers import CenterLibrary, solve_centers
from edges import EdgeLibrary, solve_edges
from corners import CornerLibrary, solve_corners

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


def _get_libs(n):
    """按阶数返回 (中心库, 边库, 角库)，优先从缓存加载。"""
    with _lock:
        if n not in _CACHE:
            p = "4" if n == 4 else "5"
            libc = _load_lib(f"center{p}")
            if libc is None or libc.n != n:
                libc = _build_and_save(f"center{p}", CenterLibrary(n))
            libe = _load_lib(f"edge{p}")
            if libe is None or libe.n != n:
                libe = _build_and_save(f"edge{p}", EdgeLibrary(n))
            libk = _load_lib(f"corner{p}")
            if libk is None or libk.n != n:
                libk = _build_and_save(f"corner{p}", CornerLibrary(n))
            _CACHE[n] = (libc, libe, libk)
        return _CACHE[n]


def solve_444(state_str):
    """
    Solve a 4x4 cube using reduction method.
    state_str: 96-character facelet string, order U, F, R, D, B, L
    Returns: list of moves
    """
    if len(state_str) != 96:
        raise ValueError(f"State string must be 96 characters, got {len(state_str)}")

    cube = BigCube(4, state_str)
    libc, libe, libk = _get_libs(4)

    cmoves, cerr = solve_centers(cube, libc)
    if cerr:
        raise ValueError(cerr)

    emoves, eerr = solve_edges(cube, libe)
    if eerr:
        raise ValueError(eerr)

    kmoves, kerr = solve_corners(cube, libk)
    if kerr:
        raise ValueError(kerr)

    if not cube.is_solved():
        raise ValueError("求解结果未能还原魔方")

    return cmoves + emoves + kmoves
