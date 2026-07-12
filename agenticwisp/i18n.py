"""界面文案本地化:WISP_LANG 选语言(默认英文),永不抛异常。"""
import os

_STRINGS = {
    "en": {
        "state.idle": "IDLE", "state.thinking": "THINKING", "state.tool": "TOOL",
        "state.waiting": "WAITING", "state.error": "ERROR",
        "tui.col.state": "state", "tui.col.heart": "heart",
        "tui.status.waiting": "… waiting for hub",
        "tui.usage.waiting": "… waiting for usage",
        "tui.bind.quit": "quit", "tui.bind.unfocus": "overview",
        "tui.footer.focus": "focus ▸ {name}      ·      press 0 / Esc for overview",
        "tui.footer.overview": "◉ {state}      ·      {n} live      ·      press 1–9 to focus a session",
        "lamp.waiting": "… waiting for hub …",
        "lamp.unknown": "unknown state: {state}",
        "page.hint": "click a card to focus · click again to return",
        "page.waiting": "… waiting for hub",
        "hub.listening": "AgenticWisp hub listening on 127.0.0.1:{port} (Ctrl-C to quit)",
    },
    "zh": {
        "state.idle": "空闲", "state.thinking": "思考", "state.tool": "调用工具",
        "state.waiting": "等你", "state.error": "出错",
        "tui.col.state": "状态", "tui.col.heart": "心跳",
        "tui.status.waiting": "… 等待中枢",
        "tui.usage.waiting": "… 等待用量",
        "tui.bind.quit": "退出", "tui.bind.unfocus": "返回总览",
        "tui.footer.focus": "专注 ▸ {name}      ·      按 0 / Esc 返回总览",
        "tui.footer.overview": "◉ {state}      ·      {n} live      ·      按 1–9 选一个 session",
        "lamp.waiting": "… 等待中枢 …",
        "lamp.unknown": "未知状态: {state}",
        "page.hint": "点卡片专注 · 再点返回",
        "page.waiting": "… 等待中枢",
        "hub.listening": "AgenticWisp 状态中枢监听 127.0.0.1:{port}(Ctrl-C 退出)",
    },
}


def lang():
    """读 WISP_LANG;'zh' 才用中文,其余(含未设/非法)→ 'en'。"""
    return "zh" if os.environ.get("WISP_LANG") == "zh" else "en"


def t(key, **kw):
    """取当前语言文案;缺 key 回退 en,再回退 key 本身;插值/格式化出错也不崩。"""
    s = _STRINGS.get(lang(), _STRINGS["en"]).get(key)
    if s is None:
        s = _STRINGS["en"].get(key, key)
    if kw:
        try:
            return s.format(**kw)
        except Exception:
            return s
    return s


def state_label(state):
    """本地化状态名;未知状态 → 原始字符串。"""
    key = "state." + str(state)
    if key not in _STRINGS["en"]:
        return str(state)
    return t(key)
