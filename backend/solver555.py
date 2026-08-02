"""
5x5 Rubik's Cube solver — 降阶法（中心 -> 边 -> 角，全部 3-cycle 贪心）。

与 solver444 相同的降阶方案：不依赖 Kociemba（模型与前端 App 转层逻辑一致，
存在拆块现象，降阶后角块在 3x3 意义上不保证合法）。
用"环对易子 3-cycle 原语 + 颜色驱动贪心"依次解中心、边、角，
最终以 cube.is_solved()（每面单色）验证还原。

原语库按阶数构建一次并缓存（5x5 构建约 40s，仅首次请求承担）。
"""

import threading

from bigcube import BigCube
from centers import CenterLibrary, solve_centers
from edges import EdgeLibrary, solve_edges
from corners import CornerLibrary, solve_corners

_lock = threading.Lock()
_CACHE = {}


def _get_libs(n):
    """按阶数缓存 (中心库, 边库, 角库)。"""
    with _lock:
        if n not in _CACHE:
            libc = CenterLibrary(n)
            libc.build()
            libe = EdgeLibrary(n)
            libe.build()
            libk = CornerLibrary(n)
            libk.build()
            _CACHE[n] = (libc, libe, libk)
        return _CACHE[n]


def solve_555(state_str):
    """
    Solve a 5x5 cube using reduction method.
    state_str: 150-character facelet string, order U, F, R, D, B, L
    Returns: list of moves
    """
    if len(state_str) != 150:
        raise ValueError(f"State string must be 150 characters, got {len(state_str)}")

    cube = BigCube(5, state_str)
    libc, libe, libk = _get_libs(5)

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
