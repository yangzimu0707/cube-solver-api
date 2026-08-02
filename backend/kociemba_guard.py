"""
安全调用 kociemba.solve()。

kociemba 遇到“颜色数量合法但物理上不可解”的状态时，会长时间空转搜索，
从而拖垮 gunicorn worker（默认 30 秒无响应会被强杀），甚至导致服务崩溃。

这里把 kociemba 放到独立子进程中运行并设置硬超时：
即使它挂起或崩溃（段错误等），也不会影响主服务进程。
"""

import json
import subprocess
import sys

# 单次求解超时（秒）。前端超时是 180 秒，这里留足余量。
DEFAULT_TIMEOUT = 90


def solve_with_timeout(cube_string, timeout=DEFAULT_TIMEOUT):
    """
    在子进程中执行 kociemba.solve(cube_string)。
    返回解法字符串（空格分隔的 3x3 动作）；超时或失败时抛异常。
    """
    # 注意：这里通过 -c 传入代码、用 sys.argv[1] 传魔方串，
    # 避免魔方串内容影响命令行拼接。
    code = (
        "import json, kociemba, sys\n"
        "try:\n"
        "    r = kociemba.solve(sys.argv[1])\n"
        "    print(json.dumps({'ok': True, 'solution': r}))\n"
        "except Exception as e:\n"
        "    print(json.dumps({'ok': False, 'error': str(e)}))\n"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code, cube_string],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(
            "Kociemba 求解超时（超过 %d 秒），魔方状态可能不可解" % timeout
        )

    if proc.returncode != 0:
        # 子进程崩溃不会影响主进程
        raise RuntimeError(
            "求解进程异常退出: %s" % ((proc.stderr or "")[:200])
        )

    out = (proc.stdout or "").strip()
    if not out:
        raise RuntimeError("求解进程无输出")

    try:
        result = json.loads(out)
    except ValueError:
        raise RuntimeError("求解进程输出无法解析: %s" % out[:200])

    if not result.get("ok"):
        raise ValueError(result.get("error", "未知错误"))

    return result["solution"]


def is_valid_3x3(cube_string):
    """
    快速校验 3x3 facelet 字符串：6 种颜色（U R F D L B）必须各出现 9 次。
    不满足时无需调用 Kociemba，直接判定为无效状态。
    """
    if len(cube_string) != 54:
        return False
    for ch in "URFDLB":
        if cube_string.count(ch) != 9:
            return False
    return True
