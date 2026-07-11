"""终端灯的纯渲染函数(与 textual 解耦,便于测试)。"""
import math
import os

from agenticwisp import protocol

_PERIODS = {
    protocol.IDLE: 4.0,
    protocol.THINKING: 1.5,
    protocol.WAITING: 0.9,
    protocol.TOOL: 0.6,
    protocol.ERROR: 0.5,
}


def state_hex(state):
    return protocol.DISPLAY.get(state, {}).get("web", "#333333")


def breathe_period(state):
    """呼吸周期(秒):空闲慢、思考中、其它急促。"""
    return _PERIODS.get(state, 0.6)


def brightness(t, period):
    """随时间起伏的亮度系数,柔和范围约 0.76–1.0(避免频闪)。"""
    return 0.88 + 0.12 * math.sin(2 * math.pi * (t % period) / period)


def build_rows(sessions):
    """[{id,name,cwd,state,tool}] → [(name, cwd, state, tool_str, hex)]。"""
    rows = []
    for s in sessions:
        rows.append((s.get("name", ""), s.get("cwd", ""), s["state"],
                     s.get("tool") or "", state_hex(s["state"])))
    return rows


def fmt_duration(seconds):
    """把秒数压缩成 8s / 2m14s / 1h2m。"""
    s = int(max(0, seconds))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m{s % 60}s"
    return f"{s // 3600}h{(s % 3600) // 60}m"


def fmt_tokens(n):
    """把 token 总数压缩成 —(None) / 999 / 312k / 1.24M。"""
    if n is None:
        return "—"
    n = int(n)
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.0f}k"
    return f"{n / 1_000_000:.2f}M"


def short_cwd(cwd):
    """cwd 取末段目录名腾出横向空间;根 / 保留;空串保留。"""
    if not cwd:
        return ""
    if cwd == "/":
        return "/"
    return os.path.basename(cwd.rstrip("/")) or cwd


def fmt_cost(x):
    """美元:<=0→"$0.00";<0.01→"<$0.01";<100→"$12.47";>=100→"$1.2k"。"""
    x = float(x or 0)
    if x <= 0:
        return "$0.00"
    if x < 0.01:
        return "<$0.01"
    if x < 100:
        return f"${x:.2f}"
    return f"${x / 1000:.1f}k"


def short_model(model):
    """去 claude- 前缀便于窄面板显示;空→"?"。"""
    if not model:
        return "?"
    return model[7:] if model.startswith("claude-") else model
