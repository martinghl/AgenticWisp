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
    """扫花名册目录 → {session_id: {name, cwd, status, pid}};坏文件/缺 id/后台会话跳过。

    只保留用户在终端里亲手开的会话。Claude Code 的 daemon 会为后台 job 和预热的
    spare 会话也写花名册文件,它们标为 kind:"bg";fork/resume 出来的后台 job 常继承
    母会话相同的 name+cwd,若不过滤会在面板上显示成重复行。用 denylist(只删显式
    "bg")而非 allowlist("interactive"),这样老版不写 kind 的会话仍照常保留。"""
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
        if meta.get("kind") == "bg":     # daemon 派生的后台 job / spare,非用户会话
            continue
        out[sid] = {
            "name": _display_name(meta),
            "cwd": meta.get("cwd", ""),
            "status": meta.get("status"),
            "pid": meta.get("pid"),
        }
    return out
