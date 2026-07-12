"""赛博朋克霓虹调色板(采用 cyberpunk-neon 标准板)。纯数据 + 语义映射。
只服务 TUI 取色;浏览器灯仍用 protocol.DISPLAY,不受影响。"""
from agenticwisp import protocol

CYAN = "#0abdc6"
MAGENTA = "#ea00d9"
PINK = "#ff2a6d"
PURPLE = "#711c91"
GREEN = "#39ff14"
AMBER = "#ffb300"
PALE = "#d1f7ff"
NAVY = "#091833"
RAIL = "#123a44"   # 暗轨(未填充/未知)

_STATE_NEON = {
    protocol.IDLE: CYAN,
    protocol.THINKING: AMBER,
    protocol.TOOL: MAGENTA,
    protocol.WAITING: PALE,
    protocol.ERROR: PINK,
}


def state_hex(state):
    """TUI 霓虹状态色;未知 → RAIL。"""
    return _STATE_NEON.get(state, RAIL)


def ctx_color(frac):
    """context 占用色阶:<60% 青、60–85% 琥珀、>=85% 粉红;None → RAIL。"""
    if frac is None:
        return RAIL
    if frac < 0.60:
        return CYAN
    if frac < 0.85:
        return AMBER
    return PINK


_EFFORT_COLOR = {"low": RAIL, "medium": CYAN, "high": GREEN, "xhigh": AMBER, "max": PINK}


def effort_color(level):
    """effort 档色阶;未知/None → RAIL。"""
    return _EFFORT_COLOR.get(level, RAIL)
