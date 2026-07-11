"""AgenticWisp 终端灯:Reactor Core 一体面板(活体大灯 + 心跳列表 + 专注)。"""
import http.client
import json
import os
import time

from rich.color import Color
from rich.style import Style
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.content import Content
from textual.widgets import DataTable, Static

from agenticwisp import protocol
from agenticwisp.tui import effects, render

# 跨 SSH 时 COLORTERM 常丢失,导致 rich 退化成 16 色、流光变难看。
# 假设终端支持真彩(MobaXterm/Termius 都支持),强制 rich 用 24 位色。
os.environ.setdefault("COLORTERM", "truecolor")

DEFAULT_PORT = 9099
_HEART_W = 12       # 心跳波形宽度
_PULSE_DECAY = 0.7  # 状态切换搏动衰减秒
_TRANS = 0.6        # 状态过渡秒
_BOOT = 0.8         # 开机淡入秒
_TOKEN_SURGE_SCALE = 30000   # token delta 达此量→满幅涌动
_TOKEN_PULSE_DECAY = 2.5     # token 涌动衰减秒


def fetch_sessions(host, port, timeout=1.0):
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    conn.request("GET", "/sessions")
    data = conn.getresponse().read().decode("utf-8")
    conn.close()
    return json.loads(data)


def fetch_usage(host, port, timeout=1.0):
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    conn.request("GET", "/usage")
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


class DashboardPanel(Static):
    """表格下方的全局用量仪表盘;set_data(agg) 后渲染。黑底友好:亮字、不铺深色块。"""

    def __init__(self, **kw):
        super().__init__("", **kw)
        self._agg = None

    def set_data(self, agg):
        self._agg = agg
        self.update(self._render())

    @property
    def renderable(self):
        """暴露当前渲染内容供测试读取(textual 8.x 的 Static 不再自带公开的 renderable 属性)。"""
        return self._render()

    def _render(self):
        # 注意:_render 与 Widget._render()(textual 内部私有方法,绘制管线用它取 Visual)同名,
        # 子类覆盖后绘制管线调用的就是这个方法 —— 必须返回 Visual(Content),
        # 若直接返回裸 rich.Text 会在挂载后的 Visual.to_strips 处崩溃(无 render_strips)。
        return Content.from_rich_text(self._render_text())

    def _render_text(self):
        a = self._agg
        if not a:
            return Text("… 等待用量", style="#22b8cf")
        t = Text()
        t.append("─ USAGE · global\n", style="#8b5cf6 bold")
        t.append(f" cost ≈ {render.fmt_cost(a.get('cost_usd', 0))}", style="#d2aa1e bold")
        t.append(f"   in {render.fmt_tokens(a.get('in', 0))}"
                 f"  out {render.fmt_tokens(a.get('out', 0))}"
                 f"  cache {render.fmt_tokens(a.get('cache', 0))}\n", style="white")
        t.append(f" turns {a.get('turns', 0)}   ·  {a.get('sessions', 0)} live"
                 f"  ·  web {a.get('web_search', 0)}/{a.get('web_fetch', 0)}\n", style="#8899aa")
        total = a.get("cost_usd", 0) or 1.0
        for r in a.get("by_model", [])[:3]:
            n = max(0, min(10, int(round((r.get("cost_usd", 0) / total) * 10))))
            bar = "▓" * n + "░" * (10 - n)
            t.append(f" ● {render.short_model(r.get('model'))}"
                     f"  {r.get('turns', 0)}t  {render.fmt_cost(r.get('cost_usd', 0))}  ", style="#22a04a")
            t.append(bar + "\n", style="#8b5cf6")
        return t


class WispApp(App):
    CSS = """
    Screen { layout: vertical; }
    #reactor { height: 11; }
    #status { height: 1; content-align: center middle; color: white; text-style: bold; }
    #table { height: 1fr; }
    #dash { height: 7; }
    """
    BINDINGS = [("q", "quit", "退出"), ("escape", "unfocus", "返回总览")]

    def __init__(self, host="127.0.0.1", port=DEFAULT_PORT, poll=0.5):
        super().__init__()
        self.host, self.port, self.poll = host, port, poll
        self._focus_id = None
        self._session_ids = []
        self._row_state = {}      # row_key → 当前状态(检测变化以触发搏动)
        self._last_change = {}    # row_key → 上次状态变化时间
        self._rows = []           # [(row_key, state)] 供动画
        self._last_tokens = {}    # sid → 上次 token 总数(算 delta)
        self._token_surge = {}    # sid → 当前涌动幅度 0..1
        self._token_surge_at = {} # sid → 涌动触发时刻
        self._t0 = time.monotonic()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield ReactorCore(id="reactor")
            yield Static("… 等待中枢", id="status")
            yield DataTable(id="table")
            yield DashboardPanel(id="dash")

    def on_mount(self):
        table = self.query_one("#table", DataTable)
        table.add_columns("#", "session", "cwd", "状态", "工具")
        table.add_column("心跳", key="heart")
        table.add_column("time", key="time")
        table.add_column("token", key="tok")
        table.cursor_type = "none"  # 用数字键选,不靠光标
        self.set_interval(self.poll, self.refresh_state)
        self.set_interval(1 / 5, self.animate_heartbeats)  # 5fps,只动心跳单元格

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
            self.query_one("#dash", DashboardPanel).set_data(None)
            return
        now = time.monotonic() - self._t0
        # 展开成显示行:父 session + 其每个子agent
        display = []   # (row_key, kind, cols, state)  kind: "sess"|"sub"
        for i, s in enumerate(sessions, start=1):
            display.append((s["id"], "sess", i, s))
            for sub in s.get("subagents", []):
                display.append((f"{s['id']}\x00{sub['id']}", "sub", None, sub))
        # 状态变化 → 搏动;清理消失行
        seen = set()
        for key, kind, _num, obj in display:
            seen.add(key)
            if self._row_state.get(key) != obj["state"]:
                self._last_change[key] = now
            self._row_state[key] = obj["state"]
        for k in list(self._row_state):
            if k not in seen:
                self._row_state.pop(k, None); self._last_change.pop(k, None)
        self._session_ids = [s["id"] for s in sessions]          # 数字键只选父
        # token 上涨 → 记录一次涌动(仅父 session)
        for s in sessions:
            sid = s["id"]; tok = s.get("tokens")
            if tok is None:
                continue
            prev = self._last_tokens.get(sid)
            if prev is not None and tok - prev > 0:
                self._token_surge[sid] = min(1.0, (tok - prev) / _TOKEN_SURGE_SCALE)
                self._token_surge_at[sid] = now
            self._last_tokens[sid] = tok
        live = set(self._session_ids)
        for d in (self._last_tokens, self._token_surge, self._token_surge_at):
            for k in list(d):
                if k not in live:
                    d.pop(k, None)
        self._rows = [(key, obj["state"]) for key, _k, _n, obj in display]
        # 焦点失效则清除
        focused = next((s for s in sessions if s["id"] == self._focus_id), None)
        if self._focus_id and focused is None:
            self._focus_id = None
        agg = protocol.aggregate(
            [s["state"] for s in sessions] +
            [sub["state"] for s in sessions for sub in s.get("subagents", [])])
        if focused:
            agg = focused["state"]
        self.query_one("#reactor", ReactorCore).set_state(agg)
        if focused:
            self.query_one("#status", Static).update(
                f"专注 ▸ {focused.get('name', '')}      ·      按 0 / Esc 返回总览")
        else:
            zh = protocol.DISPLAY.get(agg, {}).get("label", agg)
            self.query_one("#status", Static).update(
                f"◉ {zh}      ·      {len(sessions)} live      ·      按 1–9 选一个 session")
        table = self.query_one("#table", DataTable)
        table.clear()
        for key, kind, num, obj in display:
            state = obj["state"]
            hexc = render.state_hex(state)
            beat = effects.heartbeat(state, now, _HEART_W, phase=self._phase(key),
                                     pulse=min(1.0, self._pulse(key, now) + self._token_pulse(key, now)))
            dur = render.fmt_duration(now - self._last_change.get(key, now))
            if kind == "sess":
                mark = "▸" if obj["id"] == self._focus_id else " "
                nm = obj.get("name", "")
                cwd = render.short_cwd(obj.get("cwd", ""))
                tool = obj.get("tool") or ""
                num_col = f"{mark}{num}"
                tok = render.fmt_tokens(obj.get("tokens"))
            else:
                nm = f"  ↳ {obj.get('type', 'agent')}"
                cwd, tool = "", (obj.get("tool") or "")
                num_col = " "
                tok = "—"
            table.add_row(num_col, nm, cwd, Text(f"● {state}", style=hexc), tool,
                          Text(beat, style=hexc), dur, tok, key=key)
        try:
            self.query_one("#dash", DashboardPanel).set_data(
                fetch_usage(self.host, self.port, timeout=1.0))
        except Exception:
            pass

    def _phase(self, key):
        return (sum(ord(c) for c in key) % 100) / 100.0 * 6.2832

    def _pulse(self, key, now):
        return max(0.0, 1.0 - (now - self._last_change.get(key, -10.0)) / _PULSE_DECAY)

    def _token_pulse(self, key, now):
        if "\x00" in key:                       # 子行不吃 token 涌动
            return 0.0
        mag = self._token_surge.get(key, 0.0)
        if mag <= 0.0:
            return 0.0
        return mag * max(0.0, 1.0 - (now - self._token_surge_at.get(key, -1e9)) / _TOKEN_PULSE_DECAY)

    def animate_heartbeats(self):
        now = time.monotonic() - self._t0
        table = self.query_one("#table", DataTable)
        for key, state in self._rows:
            beat = effects.heartbeat(state, now, _HEART_W, phase=self._phase(key),
                                     pulse=min(1.0, self._pulse(key, now) + self._token_pulse(key, now)))
            try:
                table.update_cell(key, "heart", Text(beat, style=render.state_hex(state)))
                table.update_cell(key, "time", render.fmt_duration(now - self._last_change.get(key, now)))
            except Exception:
                pass


def run_app(argv=None):
    port = int(os.environ.get("WISP_PORT", DEFAULT_PORT))
    WispApp(port=port).run()
    return 0
