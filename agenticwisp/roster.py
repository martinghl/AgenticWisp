"""读 Claude Code 的 session 花名册 ~/.claude/sessions/*.json。纯标准库。"""
import json
import os


def _display_name(meta):
    """显示名:name > cwd 目录名 > sessionId 前 8 位 > unknown。"""
    name = meta.get("name")
    if name:
        return name
    cwd = meta.get("cwd")
    if cwd:
        return os.path.basename(cwd.rstrip("/")) or cwd
    sid = meta.get("sessionId") or ""
    return sid[:8] if sid else "unknown"


def read_roster(sessions_dir="~/.claude/sessions"):
    """扫花名册目录 → {session_id: {name, cwd, status, pid}};坏文件/缺 id 跳过。"""
    d = os.path.expanduser(sessions_dir)
    out = {}
    try:
        files = os.listdir(d)
    except OSError:
        return out
    for fn in files:
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, fn)) as f:
                meta = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict):
            continue
        sid = meta.get("sessionId")
        if not sid:
            continue
        out[sid] = {
            "name": _display_name(meta),
            "cwd": meta.get("cwd", ""),
            "status": meta.get("status"),
            "pid": meta.get("pid"),
        }
    return out
