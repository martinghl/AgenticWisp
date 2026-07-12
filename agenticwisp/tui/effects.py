"""Reactor Core 动画数学:纯函数,零依赖,便于单测。"""
import math

from agenticwisp.tui.render import breathe_period, brightness  # noqa: F401
from agenticwisp import palette


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
    """产出 h×w 字符网格,每格 [char, fg|None, bg]。赛博朋克:霓虹等离子 + 数据雨 + 扫描线 + glitch + HUD 标题。"""
    if from_state is not None and trans_p < 1.0:
        base = transition_color(palette.state_hex(from_state), palette.state_hex(state), trans_p)
    else:
        base = palette.state_hex(state)
    breath = brightness(t, breathe_period(state))
    field = plasma_field(w, h, t) if fancy else None
    rain = datarain(w, h, t) if fancy else None
    grid = []
    for y in range(h):
        row = []
        sl = scanline(y, h, t) if fancy else 1.0
        for x in range(w):
            k = (0.30 + 0.55 * field[y][x]) if fancy else 0.6
            bg = shade(base, min(1.0, k * breath * sl))
            ch, fg = " ", None
            if rain is not None:
                rch, rb = rain[y][x]
                if rch != " " and rb > 0.15:
                    ch = rch
                    fg = shade(palette.CYAN, 0.25 + 0.35 * rb)   # 暗青雨字
            row.append([ch, fg, bg])
        grid.append(row)
    # HUD 标题(顶行居中,全角 + 棱形括号,微 glitch)
    title = glitch(hud_title(state.upper() if state else "REACTOR"), t, rate=0.05) if fancy \
        else hud_title(state or "REACTOR")
    # HUD 标题放最上一行(不居中),边界检查针对实际网格
    if grid:
        x0 = max(0, (w - len(title)) // 2)
        for j, ch in enumerate(title):
            x = x0 + j
            if ch != " " and 0 <= x < w:
                grid[0][x] = [ch, _WHITE, grid[0][x][2]]
    # 中央大字 banner(走 glitch)
    eng, _zh = banner(state)
    eng2 = glitch(eng, t, rate=0.06) if fancy else eng
    rule = "─" * len(eng2)
    _place_lines(grid, w, h, [rule, eng2, rule], _WHITE)
    return grid


# 心跳波形:(base 基线, amp 振幅, speed 速度) —— 越忙越高越快
_BEAT = {
    "idle":     (1.0, 0.8, 0.7),
    "thinking": (2.5, 1.3, 1.3),
    "waiting":  (3.3, 1.6, 1.7),
    "tool":     (4.0, 2.0, 2.2),
    "error":    (4.5, 2.2, 2.6),
}


def heartbeat(state, t, width=12, phase=0.0, pulse=0.0):
    """一条随时间跳动的波形字符串;动的方式编码忙碌度,pulse 是状态切换的搏动。"""
    base, amp, speed = _BEAT.get(state, _BEAT["idle"])
    out = []
    for x in range(width):
        level = base + pulse * 2.5 + amp * math.sin(x * 0.9 + t * speed + phase)
        out.append(_BLOCKS[max(0, min(8, int(round(level))))])
    return "".join(out)


def _fullwidth(s):
    out = []
    for ch in s.upper():
        o = ord(ch)
        if ch == " ":
            out.append("　")
        elif 0x21 <= o <= 0x7e:
            out.append(chr(o + 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


def hud_title(s):
    """全角化 + 棱形括号:'usage' → '【 ＵＳＡＧＥ 】'。"""
    return "【 " + _fullwidth(s) + " 】"


def gauge(frac, width=8):
    """霓虹迷你仪表:█ 填充 / ░ 空;返回 (str, 色阶色)。None/越界安全。"""
    f = 0.0 if frac is None else max(0.0, min(1.0, frac))
    n = max(0, min(width, int(round(f * width))))
    return "█" * n + "░" * (width - n), palette.ctx_color(frac)


def scanline(row_idx, h, t):
    """扫描线亮度系数:一条随 t 缓慢下移的亮行提亮(>1)+ 奇数行轻压暗。"""
    if h <= 0:
        return 1.0
    pos = (t * 3.0) % h
    d = min(abs(row_idx - pos), h - abs(row_idx - pos))
    bright = 1.0 + 0.6 * max(0.0, 1.0 - d)
    alt = 0.92 if (row_idx % 2 == 1) else 1.0
    return bright * alt


_GLITCH_GLYPHS = "▓▒░#%&01"


def glitch(s, t, rate=0.08):
    """偶发字符替换(确定性:由 t 量化 tick 与位置决定);多数帧近乎原样。"""
    tick = int(t * 6)
    out = []
    for i, ch in enumerate(s):
        if ch != " " and ((tick * 2654435761 + i * 40503) % 997) / 997.0 < rate:
            out.append(_GLITCH_GLYPHS[(tick + i) % len(_GLITCH_GLYPHS)])
        else:
            out.append(ch)
    return "".join(out)


_KANA = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉ01"


def datarain(w, h, t):
    """暗背景数据雨:每列一个下落头(半角片假名),亮头暗尾。返回 h×w 的 [(char, bright)]。"""
    grid = [[(" ", 0.0) for _ in range(w)] for _ in range(h)]
    for x in range(w):
        speed = 2.0 + (x * 7 % 5)
        length = 3 + (x * 13 % 4)
        head = (t * speed + x * 3) % (h + length)
        for k in range(length):
            y = int(head) - k
            if 0 <= y < h:
                b = max(0.0, 1.0 - k / float(length))
                ch = _KANA[(x * 31 + int(head) - k) % len(_KANA)]
                grid[y][x] = (ch, b)
    return grid


def energybar(frac, width, t, color=None):
    """霓虹能量条:填充段 █(带一段流动高光 PALE)+ 暗轨 ░。返回 [(char, hex)]。"""
    f = 0.0 if frac is None else max(0.0, min(1.0, frac))
    n = max(0, min(width, int(round(f * width))))
    color = color or palette.MAGENTA
    hi = int((t * 6) % max(1, width))
    out = []
    for i in range(width):
        if i < n:
            out.append(("█", palette.PALE if i == hi else color))
        else:
            out.append(("░", palette.RAIL))
    return out


def neon_pulse(state, t, width=12, phase=0.0, pulse=0.0):
    """霓虹数据脉冲心跳:一个亮头顺条流动 + 渐暗拖尾 + 基线;pulse(token涌动)抬高。"""
    base, amp, speed = _BEAT.get(state, _BEAT["idle"])
    head = (t * speed + phase) % width
    out = []
    for x in range(width):
        d = min(abs(x - head), width - abs(x - head))
        wave = amp * max(0.0, 1.0 - d / 3.0)
        level = base * 0.6 + pulse * 2.5 + wave * 1.5
        out.append(_BLOCKS[max(0, min(8, int(round(level))))])
    return "".join(out)
