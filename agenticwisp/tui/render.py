"""终端灯的纯渲染函数(与 textual 解耦,便于测试)。"""
import math

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
