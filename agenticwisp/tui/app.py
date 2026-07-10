"""AgenticWisp 终端灯:Reactor Core 一体面板(活体大灯 + 心跳列表 + 专注)。"""
import http.client
import json
import os
import time
from collections import deque

from rich.color import Color
from rich.style import Style
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from agenticwisp import protocol
from agenticwisp.tui import effects, render

# 跨 SSH 时 COLORTERM 常丢失,导致 rich 退化成 16 色、流光变难看。
# 假设终端支持真彩(MobaXterm/Termius 都支持),强制 rich 用 24 位色。
os.environ.setdefault("COLORTERM", "truecolor")

DEFAULT_PORT = 9099
_HIST = 12          # 心跳采样长度
_TRANS = 0.6        # 状态过渡秒
_BOOT = 0.8         # 开机淡入秒


def fetch_sessions(host, port, timeout=1.0):
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    conn.request("GET", "/sessions")
    data = conn.getresponse().read().decode("utf-8")
    conn.close()
    return json.loads(data)


class ReactorCore(Static):
    """自定义 widget:每帧把 effects.compose_core 的网格渲染成 Rich Text。"""

    def __init__(self, **kw):
        super().__init__("", **kw)
        self._state = "idle"
        self._from_state = None
        self._trans_start = 0.0
        self._t0 = time.monotonic()
        # 默认开启花哨模式(流光/粒子);想要纯色块极简版设 WISP_PLAIN=1。
        self._plain = os.environ.get("WISP_PLAIN", "") == "1"

    def on_mount(self):
        # 6fps:跨洋 SSH 上每帧全屏重绘代价高,降频显著减卡顿(本地可调高)。
        self.set_interval(1 / 6, self.refresh)

    def set_state(self, state):
        if state != self._state:
            self._from_state = self._state
            self._trans_start = time.monotonic() - self._t0
            self._state = state

    def render(self):
        w, h = self.size.width, self.size.height
        if w <= 0 or h <= 0:
            return Text("")
        t = time.monotonic() - self._t0
        boot = min(1.0, t / _BOOT)
        trans_p = 1.0 if self._from_state is None else min(1.0, (t - self._trans_start) / _TRANS)
        fancy = (not self._plain) and w >= 24 and h >= 5
        grid = effects.compose_core(w, h, self._state, t,
                                    from_state=self._from_state, trans_p=trans_p, fancy=fancy)
        text = Text()
        for y, row in enumerate(grid):
            for ch, fg, bg in row:
                bg2 = (int(bg[0] * boot), int(bg[1] * boot), int(bg[2] * boot))
                style = Style(bgcolor=Color.from_rgb(*bg2),
                              color=(Color.from_rgb(*fg) if fg else None), bold=True)
                text.append(ch, style)
            if y < len(grid) - 1:
                text.append("\n")
        return text


class WispApp(App):
    CSS = """
    Screen { layout: vertical; }
    #reactor { height: 11; }
    #status { height: 1; content-align: center middle; color: white; text-style: bold; }
    #table { height: 1fr; }
    """
    BINDINGS = [("q", "quit", "退出"), ("escape", "unfocus", "返回总览")]

    def __init__(self, host="127.0.0.1", port=DEFAULT_PORT, poll=0.5):
        super().__init__()
        self.host, self.port, self.poll = host, port, poll
        self._focus_id = None
        self._history = {}
        self._session_ids = []

    def compose(self) -> ComposeResult:
        with Vertical():
            yield ReactorCore(id="reactor")
            yield Static("… 等待中枢", id="status")
            yield DataTable(id="table")

    def on_mount(self):
        table = self.query_one("#table", DataTable)
        table.add_columns("#", "session", "cwd", "状态", "工具", "心跳")
        table.cursor_type = "none"  # 用数字键选,不靠光标
        self.set_interval(self.poll, self.refresh_state)

    def action_unfocus(self):
        self._focus_id = None

    def on_key(self, event):
        # 数字键选一个 session 专注;0 / Esc 回总览
        if event.key in "123456789":
            i = int(event.key) - 1
            if 0 <= i < len(self._session_ids):
                self._focus_id = self._session_ids[i]
        elif event.key == "0":
            self._focus_id = None

    def refresh_state(self):
        try:
            sessions = fetch_sessions(self.host, self.port, timeout=1.0)
        except Exception:
            self.query_one("#status", Static).update("… 等待中枢")
            return
        # 采样心跳(用全量 sessions,保证历史连续),并清理消失的 session
        seen = set()
        for s in sessions:
            seen.add(s["id"])
            self._history.setdefault(s["id"], deque(maxlen=_HIST)).append(
                effects.state_level(s["state"]))
        for k in list(self._history):
            if k not in seen:
                del self._history[k]
        self._session_ids = [s["id"] for s in sessions]
        # 焦点失效(session 已消失)则清除
        focused = next((s for s in sessions if s["id"] == self._focus_id), None)
        if self._focus_id and focused is None:
            self._focus_id = None
        # 聚合态:专注则用该 session 的态,否则全局聚合
        agg = focused["state"] if focused else protocol.aggregate(s["state"] for s in sessions)
        self.query_one("#reactor", ReactorCore).set_state(agg)
        # 状态行:明写怎么选
        if focused:
            self.query_one("#status", Static).update(
                f"专注 ▸ {focused.get('name', '')}      ·      按 0 / Esc 返回总览")
        else:
            zh = protocol.DISPLAY.get(agg, {}).get("label", agg)
            self.query_one("#status", Static).update(
                f"◉ {zh}      ·      {len(sessions)} live      ·      按 1–9 选一个 session")
        # 表格:全部显示,带编号 + 焦点标记(▸)
        table = self.query_one("#table", DataTable)
        table.clear()
        for i, (s, (name, cwd, state, tool, hexc)) in enumerate(
                zip(sessions, render.build_rows(sessions)), start=1):
            mark = "▸" if s["id"] == self._focus_id else " "
            spark = effects.sparkline(list(self._history.get(s["id"], [])), width=_HIST)
            table.add_row(f"{mark}{i}", name, cwd, Text(f"● {state}", style=hexc), tool,
                          Text(spark, style=hexc), key=s["id"])


def run_app(argv=None):
    port = int(os.environ.get("WISP_PORT", DEFAULT_PORT))
    WispApp(port=port).run()
    return 0
