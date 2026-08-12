"""DeepSeek 大模型教学服务（通过 Render 服务器代理，避免前端直接暴露 API Key）

前端请求 /ai/chat -> 本模块调用 DeepSeek Chat Completions API -> 返回回答文本。
"""
import os
import requests

# 从 Render 环境变量读取，切勿把 Key 写死在代码/仓库里
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_TIMEOUT = 180
MAX_HISTORY_MESSAGES = 12  # 只保留最近 N 条对话，避免上下文过长拖慢响应

# 魔方状态字符串格式说明（与前端 CubeState.toCubeString 完全一致）
CUBE_FORMAT_DESC = """
魔方状态字符串格式（长度 = 阶数²×6，即 2x2=24 / 3x3=54 / 4x4=96 / 5x5=150 字符）：
- 按面顺序 U, F, R, D, B, L 依次拼接，每个面 n×n 个贴纸按行优先（第1行第1列→第n行第n列）。
- 颜色字母：U=白色(顶面), D=黄色(底面), F=红色(前面), B=橙色(后面), L=绿色(左面), R=蓝色(右面)。
- 例如 3x3 字符串的前 9 个字符就是 U 面（白面）从上到下、从左到右的贴纸。
- 移动记号：U/U'/U2、D/D'/D2、F/F'/F2、B/B'/B2、L/L'/L2、R/R'/R2（' 表示逆时针 90°，2 表示 180°）。
  4x4/5x5 还可能有宽层记号如 TR/TL/TU/TD/TU'/TR2 等，5x5 有中间层 M/M'/E/E'/S/S'。
"""

SYSTEM_PROMPT_CHAT = (
    "你是一位专业、耐心、友好的魔方还原教练，精通 2x2/3x3/4x4/5x5 魔方。"
    "你可以讲解任何魔方问题：还原公式、手法技巧、层先法/CFOP/降阶法等思路、卡在某一步怎么处理等。"
    "回答一律用简体中文，条理清晰；公式用代码块或加粗展示，必要时分步骤列出。"
    "如果提供了用户当前的魔方状态字符串，请结合该状态给出针对性的建议；"
    "若状态不足以准确判断，请说明原因并给出通用的教学建议。"
    + CUBE_FORMAT_DESC
)

SYSTEM_PROMPT_GUIDED = (
    "你是一位魔方还原教练，正在一步一步地指导用户还原魔方。"
    "用户每次请求只允许走一步。你必须严格遵守以下输出格式："
    "先输出 [移动]（例如 [R]、[U']、[F2]、[M']），然后换行用一句简短的中文解释这一步的目的和做法。"
    "一次只给一步，不要给整段公式序列，不要多余废话。"
    "仅允许使用 U/U'/U2、D/D'/D2、F/F'/F2、B/B'/B2、L/L'/L2、R/R'/R2（5x5 可附加 M/M'/M2、E/E'/E2、S/S'/S2；"
    "4x4/5x5 可附加宽层 TR/TL/TU/TD/TU'/TR2 等）。"
    "每一步都要合法且合理，优先采用最经典、最易学的还原方法（如 3x3 用层先法：十字→角块→中层→顶面→顶层）。"
    "如果用户表示魔方已还原，或你判断魔方已经还原，则回复 [DONE] 并附上一句祝贺。"
    + CUBE_FORMAT_DESC
)


def _build_system_prompt(mode: str, cube: str | None) -> str:
    if mode == "guided":
        return SYSTEM_PROMPT_GUIDED
    if cube:
        return SYSTEM_PROMPT_CHAT + f"\n\n用户当前的魔方状态字符串（{len(cube)} 字符）：{cube}"
    return SYSTEM_PROMPT_CHAT


def chat_with_deepseek(messages, mode="chat", cube=None, temperature=0.7, max_tokens=1200):
    """调用 DeepSeek Chat Completions，返回回答文本。

    messages: [{"role": "user"|"assistant"|"system", "content": "..."}, ...]
    mode: "chat" 聊天问答 | "guided" 逐步引导
    cube: 前端传来的魔方状态字符串（可选）
    """
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("服务器未配置 DEEPSEEK_API_KEY，请在 Render 环境变量中添加")

    payload_messages = [{"role": "system", "content": _build_system_prompt(mode, cube)}]
    recent = messages[-MAX_HISTORY_MESSAGES:] if messages else []
    for m in recent:
        role = m.get("role", "user")
        if role not in ("user", "assistant", "system"):
            continue
        payload_messages.append({"role": role, "content": m.get("content", "")})

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": payload_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    resp = requests.post(DEEPSEEK_URL, headers=headers, json=body, timeout=DEEPSEEK_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"DeepSeek API 错误 (HTTP {resp.status_code}): {resp.text[:500]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"DeepSeek API 返回格式异常: {str(data)[:500]}")
