"""解析 Claude Code transcript(.jsonl)累计 token 用量。纯标准库,无状态。"""
import glob
import json
import os

_USAGE_KEYS = ("input_tokens", "output_tokens",
               "cache_read_input_tokens", "cache_creation_input_tokens")


def _as_int(v):
    """安全地将值转为 int,坏值 → 0。"""
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def find_transcript(session_id, projects_dir="~/.claude/projects"):
    """glob 定位 <projects_dir>/*/<session_id>.jsonl;命中返首个,否则 None。"""
    if not session_id:
        return None
    base = os.path.expanduser(projects_dir)
    hits = glob.glob(os.path.join(base, "*", glob.escape(session_id) + ".jsonl"))
    return hits[0] if hits else None


def _line_tokens(raw):
    try:
        d = json.loads(raw)
    except ValueError:
        return 0
    msg = d.get("message") if isinstance(d, dict) else None
    u = msg.get("usage") if isinstance(msg, dict) else None
    if not isinstance(u, dict):
        return 0
    return sum(_as_int(u.get(k)) for k in _USAGE_KEYS)


def _read_new_complete(path, offset):
    """从 offset 读出新增的完整行(bytes 列表,已去空行)+ 新offset。
    size<offset→从头;末尾无 \\n 的半行不越过;IO失败/无整行→([], 0或offset)。"""
    try:
        size = os.path.getsize(path)
    except OSError:
        return ([], 0)
    if size < offset:
        offset = 0
    if size == offset:
        return ([], offset)
    try:
        with open(path, "rb") as f:
            f.seek(offset)
            chunk = f.read(size - offset)
    except OSError:
        return ([], offset)
    nl = chunk.rfind(b"\n")
    if nl < 0:
        return ([], offset)
    complete = chunk[:nl + 1]
    lines = [r for r in complete.split(b"\n") if r.strip()]
    return (lines, offset + len(complete))


def scan_usage(path, offset):
    """从 offset 读新增的完整行,累加 token。返回 (新增token, 新offset)。"""
    lines, new_off = _read_new_complete(path, offset)
    added = sum(_line_tokens(r.decode("utf-8", "replace")) for r in lines)
    return (added, new_off)


def _line_detail(raw):
    """→ (model, {in,out,cr,cc}, web_search, web_fetch) 或 None(非usage行)。"""
    try:
        d = json.loads(raw)
    except ValueError:
        return None
    msg = d.get("message") if isinstance(d, dict) else None
    u = msg.get("usage") if isinstance(msg, dict) else None
    if not isinstance(u, dict):
        return None
    model = msg.get("model") or "unknown"
    comp = {"in": _as_int(u.get("input_tokens")), "out": _as_int(u.get("output_tokens")),
            "cr": _as_int(u.get("cache_read_input_tokens")),
            "cc": _as_int(u.get("cache_creation_input_tokens"))}
    stu = u.get("server_tool_use")
    ws = _as_int(stu.get("web_search_requests")) if isinstance(stu, dict) else 0
    wf = _as_int(stu.get("web_fetch_requests")) if isinstance(stu, dict) else 0
    return (model, comp, ws, wf)


def scan_usage_detailed(path, offset):
    """从 offset 读新增完整行,按模型累加明细 + web计数。返回 (detail, 新offset)。"""
    lines, new_off = _read_new_complete(path, offset)
    models = {}
    ws_total = wf_total = 0
    for r in lines:
        parsed = _line_detail(r.decode("utf-8", "replace"))
        if parsed is None:
            continue
        model, comp, ws, wf = parsed
        m = models.setdefault(model, {"in": 0, "out": 0, "cr": 0, "cc": 0, "turns": 0})
        for k in ("in", "out", "cr", "cc"):
            m[k] += comp[k]
        m["turns"] += 1
        ws_total += ws
        wf_total += wf
    return ({"models": models, "web_search": ws_total, "web_fetch": wf_total}, new_off)
