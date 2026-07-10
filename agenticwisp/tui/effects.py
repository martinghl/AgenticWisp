"""Reactor Core 动画数学:纯函数,零依赖,便于单测。"""
import math

from agenticwisp.tui.render import state_hex, breathe_period, brightness  # noqa: F401


def _to_rgb(color):
    if isinstance(color, (tuple, list)):
        return int(color[0]), int(color[1]), int(color[2])
    h = color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def shade(color, k):
    """按 k∈[0,1] 等比缩放亮度,色相不变。含 0.15 下限:k=0 也不纯黑(黑底友好)。"""
    r, g, b = _to_rgb(color)
    f = 0.15 + 0.85 * max(0.0, min(1.0, k))
    return min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f))


def transition_color(from_color, to_color, p):
    """线性插值 rgb;p=0→from,p=1→to。"""
    p = max(0.0, min(1.0, p))
    fr, fg, fb = _to_rgb(from_color)
    tr, tg, tb = _to_rgb(to_color)
    return (int(fr + (tr - fr) * p), int(fg + (tg - fg) * p), int(fb + (tb - fb) * p))


def plasma_field(cols, rows, t):
    """等离子强度场,每值∈[0,1]。t 放慢让流动更缓、SSH 上更顺。"""
    t = t * 0.35
    field = []
    for y in range(rows):
        line = []
        for x in range(cols):
            v = (math.sin(x / 4.0 + t)
                 + math.sin(y / 3.0 - t * 0.8)
                 + math.sin((x + y) / 5.0 + t * 0.5)
                 + math.sin(math.hypot(x - cols / 2.0, y - rows / 2.0) / 4.0 - t))
            line.append((v + 4.0) / 8.0)
        field.append(line)
    return field


_BLOCKS = " ▁▂▃▄▅▆▇█"          # 索引 0..8
_PCHARS = "✦·⋆∘•"

_LEVELS = {"idle": 1, "thinking": 3, "waiting": 4, "tool": 5, "error": 6}
_ENG = {"idle": "I D L E", "thinking": "T H I N K I N G", "tool": "T O O L",
        "waiting": "W A I T I N G", "error": "E R R O R"}
_ZH = {"idle": "空闲", "thinking": "思考", "tool": "调用工具",
       "waiting": "等你", "error": "出错"}


def state_level(state):
    return _LEVELS.get(state, 0)


def sparkline(levels, width=None):
    levels = list(levels)
    if width is not None:
        levels = levels[-width:]
        levels = [0] * (width - len(levels)) + levels
    return "".join(_BLOCKS[max(0, min(8, int(l)))] for l in levels)


def banner(state):
    return _ENG.get(state, state.upper()), _ZH.get(state, "")


def particles(t, n, w, h):
    out = []
    cx, cy = w / 2.0, h / 2.0
    radius = max(1.0, min(w, h * 2) / 2.2)
    for i in range(n):
        ang = t * 0.9 + i * (2 * math.pi / max(1, n))
        x = int(round(cx + radius * math.cos(ang)))
        y = int(round(cy + (radius / 2.0) * math.sin(ang)))
        if 0 <= x < w and 0 <= y < h:
            inten = 0.5 + 0.5 * math.sin(t * 2.0 + i)
            out.append((x, y, _PCHARS[i % len(_PCHARS)], inten))
    return out


_WHITE = (240, 240, 255)


def _place_lines(grid, w, h, lines, color):
    """把若干行文字居中叠加到网格(仅覆盖非空格字符的前景)。"""
    start_y = max(0, h // 2 - len(lines) // 2)
    for i, line in enumerate(lines):
        y = start_y + i
        if not (0 <= y < h):
            continue
        x0 = max(0, (w - len(line)) // 2)
        for j, ch in enumerate(line):
            x = x0 + j
            if 0 <= x < w and ch != " ":
                grid[y][x] = [ch, color, grid[y][x][2]]


def compose_core(w, h, state, t, from_state=None, trans_p=1.0, fancy=True):
    """产出 h×w 字符网格,每格 [char, fg|None, bg]。"""
    if from_state is not None and trans_p < 1.0:
        base = transition_color(state_hex(from_state), state_hex(state), trans_p)
    else:
        base = state_hex(state)
    breath = brightness(t, breathe_period(state))
    field = plasma_field(w, h, t) if fancy else None
    grid = []
    for y in range(h):
        row = []
        for x in range(w):
            k = (0.35 + 0.65 * field[y][x]) if fancy else 0.6
            row.append([" ", None, shade(base, k * breath)])
        grid.append(row)
    if fancy:
        for (px, py, ch, inten) in particles(t, 10, w, h):
            spark = shade(base, min(1.0, 0.85 + 0.3 * inten))
            fg = (min(255, spark[0] + 110), min(255, spark[1] + 110), min(255, spark[2] + 110))
            grid[py][px] = [ch, fg, grid[py][px][2]]
    eng, _zh = banner(state)
    rule = "─" * len(eng)
    _place_lines(grid, w, h, [rule, eng, rule], _WHITE)
    return grid
